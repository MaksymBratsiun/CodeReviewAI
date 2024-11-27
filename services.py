import logging
from functools import wraps
from typing import Dict, Optional, Callable, Any, List
import configparser

import httpx
import openai
import asyncio

BRANCH = "main"
GPT_MODEL = "gpt-3.5-turbo"
MAX_TOKENS = 300
MAX_TOKEN_SUMMARY = 500
TEMPERATURE = 0.6
GITHUB_ROOT = "https://github.com/"
GITHUB_API_URL = "https://api.github.com"
VALID_EXTENSIONS = {".py", ".md", ".ini"}
BATCH_SIZE = 7

# f"{PROMPT_SYS}{description}"
PROMPT_SYS = "You are an experienced software reviewer. Evaluate the code according:"

# f"Project structure:{structure}{PROMPT...}"
PROMPT_USER_STRUCTURE = "Identifying weaknesses, issues and good solutions in 3 sentences." \
                        " Make conclusion in 1 sentences."

# f"File name: {name}\n{content}\n{PROMPT...}{level}"
PROMPT_USER_FILE_ANALYZE = "Identifying weaknesses, issues and good solutions in 2-3 sentences. " \
                           "Write a brief comment on the developer’s skills in 1 sentence for " \
                           "developer level: "

# f"{..SUMMARY_TASK}{summaries_text}{..SUMMARY_SOLUTIONS}\n{..SUMMARY_SKILLS}{..SUMMARY_RATING}{dev_level}"
PROMPT_USER_SUMMARY_TASK = "Make summary review according preview analyze:"
PROMPT_USER_SUMMARY_SOLUTIONS = "Solutions: identifying weaknesses and good solutions in 2-3 sentences."
PROMPT_USER_SUMMARY_SKILLS = "Skills: write a brief comment on the developer’s skills in 1-2 sentence."
PROMPT_USER_SUMMARY_RATING = "Rating: (from 1 to 5) for developer level: "

# f"{..REDUCE_TASK}{summaries_text}{..REDUCE_SOLUTIONS}\n{..REDUCE_SKILLS}{..REDUCE_RATING}{dev_level}"
PROMPT_USER_REDUCE_TASK = "Make summary review according preview analyze:"
PROMPT_USER_REDUCE_SOLUTIONS = "Solutions: Summarize identifying weaknesses and good solutions in 2-3 sentences."
PROMPT_USER_REDUCE_SKILLS = "Skills:Summarize brief comment on the developer’s skills in 1-2 sentence."
PROMPT_USER_REDUCE_RATING = "Rating: Summarize rating (from 1 to 5) for developer level: "

logger = logging.getLogger("services")


# Facade for analyze
async def perform_analysis(files: dict, dev_level: str, description: str) -> str:

    try:
        results_structure = await analyze_structure(files, description)
        cleaned_files = {file_path: content for file_path, content in files.items() if content is not None}
        logger.info(f"Files to analyze: {len(cleaned_files)}")

        # File analyze
        analysis_tasks = [
            analyze_file_content(name, content, dev_level, description)
            for name, content in cleaned_files.items()
        ]
        analysis_results = await asyncio.gather(*analysis_tasks)

        # Summary of results
        return await summarize_analysis(analysis_results, results_structure, dev_level, description)

    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        raise


# Summary analysis function of each file content analysis results
async def summarize_analysis(analysis_results: List[str],
                             results_structure: str,
                             dev_level: str,
                             description: str
                             ) -> str:
    """
    Summary analysis files and analysis structure into one
    :param analysis_results: List[str]
    :param results_structure: str
    :param dev_level: str
    :param description: str
    :return: str
    """
    try:
        if len(analysis_results) == 0:
            logger.info("No file content to summarize")
            return "No file content to summarize."

        if len(analysis_results) <= BATCH_SIZE:
            logger.info("Summary starts for < 7 files")
            return await analyze_summary(analysis_results, results_structure, dev_level, description)

        logger.info(f"Summary starts for > 7 files. Total: {len(analysis_results)}")
        analysis_results.append(results_structure)

        # Loop of summary results
        while len(analysis_results) >= BATCH_SIZE:
            logger.info(f"Reducing batch. Current size: {len(analysis_results)}")
            tasks = [
                analyze_reduce(analysis_results[i:i + BATCH_SIZE], dev_level, description)
                for i in range(0, len(analysis_results), BATCH_SIZE)
            ]
            analysis_results = await asyncio.gather(*tasks)

        logger.info("Final reduction")
        return await analyze_reduce(analysis_results, dev_level, description) if analysis_results else "No results"

    except Exception as e:
        logger.exception(f"Summarization failed: {e}")
        raise


def handle_api_errors(func: Callable) -> Callable:
    """
    Decorator for error handling and logging in functions working with the OpenAI API
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            # Main function implementation
            result = await func(*args, **kwargs)
            logger.info(f"Function {func.__name__} executed successfully.")
            return result
        except openai.OpenAIError as e:
            # Error handling OpenAI API
            logger.error(f"OpenAI API error in {func.__name__}: {e}")
            return f"Error: OpenAI API failed with error: {e}"
        except Exception as e:
            # Other exceptions handling
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            return f"Error: Unexpected failure in {func.__name__}: {e}"
    return wrapper


def repo_url_to_git_api_url(input_url: str) -> str | None:
    """
    The function converts GitHub Repository Link to GitHub API Link
    """
    input_url = input_url.strip().lower()
    if input_url.startswith(GITHUB_ROOT):
        res = input_url.removeprefix(GITHUB_ROOT).split("/")
        if len(res) > 1:
            owner, repo = res[0], res[1]
            return f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents"


async def get_all_files(url: str, client: httpx.AsyncClient) -> Dict[str, Optional[str]] | None:
    """
    The function return dict {FILE_NAME: TEXT of downloaded files from GitHub if they have VALID_EXTENSIONS or None}
    """
    files_dict = {}
    try:
        response = await client.get(url)
        response.raise_for_status()  # Raise exception for status code 4xx/5xx
        logger.info(f"Fetched data from {url} with status {response.status_code}")

        try:
            items = response.json()
        except ValueError as e:
            logger.error(f"Failed to parse JSON from {url}: {e}")
            return None

        # Processing each item
        for item in items:
            if item['type'] == 'file':
                file_name = item['path']
                file_extension = file_name[file_name.rfind("."):]

                if file_extension in VALID_EXTENSIONS:
                    try:
                        file_response = await client.get(item['download_url'])
                        file_response.raise_for_status()
                        files_dict[file_name] = file_response.text
                        logger.info(f"Downloaded file: {file_name}")
                    except httpx.RequestError as e:
                        logger.error(f"Failed to fetch file {file_name} from {item['download_url']}: {e}")
                        files_dict[file_name] = None
                else:
                    logger.info(f"Ignored file due to invalid extension: {file_name}")
                    files_dict[file_name] = None

            elif item['type'] == 'dir':
                try:
                    subdir_files = await get_all_files(item['_links']['self'], client)
                    if subdir_files:
                        files_dict.update(subdir_files)
                except Exception as e:
                    logger.error(f"Error processing directory {item['path']}: {e}")

    except httpx.RequestError as e:
        logger.error(f"Failed to fetch data from {url}: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error while fetching files: {e}")
        return None

    return files_dict


@handle_api_errors
async def analyze_structure(files: Dict[str, Optional[str]], description: str) -> str:
    """
    The function makes request OpenAI API about repository structure and return response string
    """
    structure = ", ".join(files.keys())
    response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system",
                 "content": f"{PROMPT_SYS}{description}"
                 },
                {"role": "user",
                 "content": f"Project structure:{structure}\n{PROMPT_USER_STRUCTURE}"
                 }
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE

        )

    return response.choices[0].message.content.strip()


@handle_api_errors
async def analyze_file_content(name: str, content: str, level: str, description: str) -> str:
    """
    The function makes request OpenAI API to analyze the file content and return response string
    """
    response = openai.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system",
                 "content": f"{PROMPT_SYS}{description}"
                 },
                {"role": "user",
                 "content": f"File name: {name}\n{content}\n{PROMPT_USER_FILE_ANALYZE}{level}"
                 }
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE

        )
    return response.choices[0].message.content.strip()


@handle_api_errors
async def analyze_summary(analysis: list, results_structure: str, dev_level: str, description: str) -> str:
    """
    The function makes request OpenAI API to summary content and return response string
    """
    analysis.append(results_structure)
    summaries_text = "\n".join(analysis)
    prompt = f"""{PROMPT_USER_SUMMARY_TASK}{summaries_text}
    {PROMPT_USER_SUMMARY_SOLUTIONS}\n{PROMPT_USER_SUMMARY_SKILLS}
    {PROMPT_USER_SUMMARY_RATING}{dev_level}
    """
    response = openai.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system",
             "content": f"{PROMPT_SYS}{description}"
             },
            {"role": "user",
             "content": prompt
             }
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE

    )

    return response.choices[0].message.content.strip()


@handle_api_errors
async def analyze_reduce(analysis_butch: list, dev_level: str, description: str) -> str:
    """
    The function makes request OpenAI API to reduce content and return response string
    """
    summaries_text = "\n".join(analysis_butch)
    prompt = f"""{PROMPT_USER_REDUCE_TASK}{summaries_text}
    {PROMPT_USER_REDUCE_SOLUTIONS}\n{PROMPT_USER_REDUCE_SKILLS}
    {PROMPT_USER_REDUCE_RATING}{dev_level}
    """
    response = openai.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system",
             "content": f"{PROMPT_SYS}{description}"
             },
            {"role": "user",
             "content": prompt
             }
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE
    )

    return response.choices[0].message.content.strip()
