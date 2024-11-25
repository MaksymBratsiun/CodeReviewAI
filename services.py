from typing import Dict, Optional

import httpx
import openai
# import asyncio

BRANCH = "main"
GPT_MODEL = "gpt-3.5-turbo"
MAX_TOKENS = 300
MAX_TOKEN_SUMMARY = 500
TEMPERATURE = 0.6
GITHUB_ROOT = "https://github.com/"
GITHUB_API_URL = "https://api.github.com"
VALID_EXTENSIONS = {".py", ".md", ".ini"}

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


def repo_url_to_git_api_url(input_url: str) -> str | None:
    input_url = input_url.strip().lower()
    if input_url.startswith(GITHUB_ROOT):
        res = input_url.removeprefix(GITHUB_ROOT).split("/")
        if len(res) > 1:
            owner, repo = res[0], res[1]
            return f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents"


async def get_all_files(url: str, client: httpx.AsyncClient) -> Dict[str, Optional[str]] | None:
    files_dict = {}
    response = await client.get(url)
    if response.status_code == 200:
        items = response.json()
        for item in items:
            if item['type'] == 'file':
                file_name = item['path']
                file_extension = file_name[file_name.rfind("."):]

                if file_extension in VALID_EXTENSIONS:
                    file_response = await client.get(item['download_url'])

                    if file_response.status_code == 200:
                        files_dict[file_name] = file_response.text
                    else:
                        files_dict[file_name] = None
                else:
                    files_dict[file_name] = None

            elif item['type'] == 'dir':

                subdir_files = await get_all_files(item['_links']['self'], client)
                files_dict.update(subdir_files)
    else:
        files_dict = None

    return files_dict


def analyze_structure(files: Dict[str, Optional[str]], description: str) -> str:
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


async def analyze_file_content(name: str, content: str, level: str, description: str) -> str:
    # loop = asyncio.get_running_loop()
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


async def analyze_summary(analysis: list, results_structure: str, dev_level: str, description: str) -> str:
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


async def analyze_reduce(analysis_butch: list, dev_level: str, description: str) -> str:
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
