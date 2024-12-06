import logging
from functools import wraps
from typing import Dict, Optional, Callable, Any

import openai

from config import config

GPT_MODEL = config.get("api_requests", "model", fallback="gpt-3.5-turbo")
MAX_TOKENS = config.getint("api_requests", "max_tokens", fallback=400)
MAX_TOKEN_SUMMARY = config.getint("api_requests", "max_token_summary", fallback=500)
TEMPERATURE = config.getfloat("api_requests", "temperature", fallback=0.6)

# f"{PROMPT_SYS}{description}"
PROMPT_SYS = config.get("api_requests", "prompt_sys_json", fallback="Evaluate the code according:")

# f"Project structure:{structure}{PROMPT...}"
PROMPT_USER_STRUCTURE = config.get("api_requests", "prompt_user_structure", fallback="Evaluate the code according:")

# f"File name: {name}\n{content}\n{PROMPT...}{level}"
PROMPT_USER_FILE_ANALYZE = config.get("api_requests", "prompt_user_file_analyze", fallback=" Evaluate the code")

# f"{..SUMMARY_TASK}{summaries_text}{..SUMMARY_SOLUTIONS}\n{..SUMMARY_SKILLS}{..SUMMARY_RATING}{dev_level}"
PROMPT_USER_SUMMARY_TASK = config.get("api_requests", "prompt_user_summary_task",
                                      fallback="Make summary review according preview analyze: ")
PROMPT_USER_SUMMARY_SOLUTIONS = config.get("api_requests", "prompt_user_summary_solutions",
                                           fallback="Solutions: identifying weaknesses and good solutions.")
PROMPT_USER_SUMMARY_SKILLS = config.get("api_requests", "prompt_user_summary_skills",
                                        fallback="Skills: write a brief comment on the developer’s skills.")
PROMPT_USER_SUMMARY_RATING = config.get("api_requests", "prompt_user_summary_rating",
                                        fallback="Rating: (from 1 to 5) for developer level:")

# f"{..REDUCE_TASK}{summaries_text}{..REDUCE_SOLUTIONS}\n{..REDUCE_SKILLS}{..REDUCE_RATING}{dev_level}"
PROMPT_USER_REDUCE_TASK = config.get("api_requests", "prompt_user_reduce_task",
                                     fallback="Make summary review according preview analyze:")
PROMPT_USER_REDUCE_SOLUTIONS = config.get("api_requests", "prompt_user_reduce_solutions",
                                          fallback="Solutions: identifying weaknesses and good solutions.")
PROMPT_USER_REDUCE_SKILLS = config.get("api_requests", "prompt_user_reduce_skills",
                                       fallback="Skills: write a brief comment on the developer’s skills.")
PROMPT_USER_REDUCE_RATING = config.get("api_requests", "prompt_user_reduce_rating",
                                       fallback="Rating: (from 1 to 5) for developer level:")

logger = logging.getLogger(__name__)


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


@handle_api_errors
async def analyze_structure(files: Dict[str, Optional[str]], description: str) -> str:

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
    Analyzes the content of a file by making a request to the OpenAI API.

    Args:
        name (str): The name of the file to be analyzed.
        content (str): The content of the file to be analyzed.
        level (str): The development level or context for the analysis.
        description (str): Additional description or context for the analysis.

    Returns:
        str: A response string from the OpenAI API containing the analysis result.

    Raises:
        openai.error.OpenAIError: If an error occurs during the API request.
        Exception: For any other errors encountered during execution.
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
