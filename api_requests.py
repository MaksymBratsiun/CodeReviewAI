import logging
from functools import wraps
from typing import Dict, Optional, Callable, Any

import openai
from openai._exceptions import OpenAIError

from config import client
from config import GPT_MODEL, MAX_TOKENS, TEMPERATURE
from config import PROMPT_SYS, PROMPT_USER_STRUCTURE, PROMPT_USER_FILE_ANALYZE
from config import PROMPT_USER_SUMMARY_TASK, PROMPT_USER_SUMMARY_SOLUTIONS
from config import PROMPT_USER_SUMMARY_SKILLS, PROMPT_USER_SUMMARY_RATING
from config import PROMPT_USER_REDUCE_TASK, PROMPT_USER_REDUCE_SOLUTIONS
from config import PROMPT_USER_REDUCE_SKILLS, PROMPT_USER_REDUCE_RATING

logger = logging.getLogger(__name__)


def handle_api_errors(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            result = await func(*args, **kwargs)
            logger.info(f"Function {func.__name__} executed successfully.")
            return result
        except OpenAIError as e:
            logger.error(f"OpenAI API error in {func.__name__}: {e}")
            return f"Error: OpenAI API failed with error: {e}"
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            return f"Error: Unexpected failure in {func.__name__}: {e}"
    return wrapper


@handle_api_errors
async def analyze_structure(files: Dict[str, Optional[str]], description: str) -> str:
    """
    A decorator to handle errors in asynchronous functions, specifically targeting OpenAI API errors.

    Args:
    func (Callable): The asynchronous function to be wrapped by the error handler.

    Returns:
    Callable: A wrapped version of the input function with error handling.

    Workflow:
    1. Executes the wrapped function asynchronously.
    2. Logs a success message if the function completes without errors.
    3. Catches and logs `openai.OpenAIError` exceptions, returning a formatted error message.
    4. Catches and logs any other unexpected exceptions, returning a generic error message.
    5. Ensures the application can gracefully handle and log exceptions from the decorated function.

    Notes:
    - This decorator is designed to work with asynchronous functions (`async def`).
    - The OpenAI-specific error handling provides better debugging for API failures.
    - General exception handling ensures robustness against unanticipated errors.
    """
    structure = ", ".join(files.keys())
    try:
        response = await client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"{PROMPT_SYS}{description}"
                },
                {
                    "role": "user",
                    "content": f"Project structure:{structure}\n{PROMPT_USER_STRUCTURE}"
                }
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE
        )

        return response.choices[0].message.content.strip()

    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise


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
    try:
        response = await client.chat.completions.create(
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

    except openai.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise


@handle_api_errors
async def analyze_summary(analysis: list, results_structure: str, dev_level: str, description: str) -> str:
    """
    Generates a summary review based on provided analysis results, developer level, and description.

    Args:
    analysis (list): A list of strings containing individual file analyses.
    results_structure (str): A string representing the structure analysis result.
    dev_level (str): The developer's level, used to customize the summary and rating.
    description (str): Additional context or description to guide the summary process.

    Returns:
    str: A structured summary generated from the input data, formatted as a string.

    Workflow:
    1. Appends the `results_structure` to the list of analyses.
    2. Concatenates the analyses into a single string with newline separation.
    3. Constructs a detailed prompt including the task, solutions, skills, and rating instructions.
    4. Sends the prompt to the OpenAI API to generate a summarized response.
    5. Returns the response content, stripped of extra whitespace.

    Raises:
    openai.OpenAIError: If the OpenAI API encounters an error.
    Exception: For any other unhandled errors during execution.
    """

    analysis.append(results_structure)
    summaries_text = "\n".join(analysis)
    prompt = f"""{PROMPT_USER_SUMMARY_TASK}{summaries_text}
    {PROMPT_USER_SUMMARY_SOLUTIONS}\n{PROMPT_USER_SUMMARY_SKILLS}
    {PROMPT_USER_SUMMARY_RATING}{dev_level}
    """
    response = await client.chat.completions.create(
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
    Generate a summary review based on the analysis of multiple files, the results structure,
    developer level, and a provided description.

    Args:
    analysis (list): A list of strings containing detailed analysis results for individual files.
    results_structure (str): A structured result summarizing the analysis of the project's overall architecture.
    dev_level (str): The developer's experience level (e.g., "Junior", "Intermediate", "Senior").
    description (str): Additional contextual information to customize the analysis and summary.

    Returns:
    str: A string containing the summarized review, including comments, skill evaluation,
         and a rating based on the developer's level.

    Raises:
    openai.OpenAIError: Raised if an error occurs while communicating with the OpenAI API.
    Exception: Raised for any other unhandled errors during execution.

    Workflow:
    1. Append the `results_structure` to the provided `analysis` list.
    2. Combine all analysis elements into a single text block separated by newlines.
    3. Create a prompt that specifies tasks, solutions, skills assessment, and rating instructions.
    4. Submit the prompt to the OpenAI API to generate a summary based on the inputs.
    5. Returns the response content, stripped of extra whitespace.
    """
    summaries_text = "\n".join(analysis_butch)
    prompt = f"""{PROMPT_USER_REDUCE_TASK}{summaries_text}
    {PROMPT_USER_REDUCE_SOLUTIONS}\n{PROMPT_USER_REDUCE_SKILLS}
    {PROMPT_USER_REDUCE_RATING}{dev_level}
    """
    response = await client.chat.completions.create(
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
