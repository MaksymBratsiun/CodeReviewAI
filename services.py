import logging
import configparser
from typing import Dict, Optional, List

import httpx
import asyncio

from config import GITHUB_ROOT, GITHUB_API_URL, BATCH_SIZE, VALID_EXTENSIONS
from api_requests import analyze_summary, analyze_reduce, analyze_structure, analyze_file_content

logger = logging.getLogger(__name__)


# Facade for analyze
async def perform_analysis(files: dict, dev_level: str, description: str) -> str:
    """
     Performs a comprehensive analysis of the provided files, generates individual file analyses,
     and creates a summary of the results.

     Args:
     files (dict): A dictionary where keys are file paths and values are file contents.
     dev_level (str): The developer's proficiency level (e.g., "junior", "mid", "senior").
     description (str): A description of the project or task to guide the analysis.

     Returns:
     str: A summary of the analysis results in JSON format.

     Raises:
     Exception: If any error occurs during the analysis process, it is logged and re-raised.

     Workflow:
     1. Make analysis the project structure by calling `analyze_structure`.
     2. Clean the input files to exclude any with `None` content.
     3. Perform content analysis on each file asynchronously using `analyze_file_content`.
     4. Summarize the analysis results along with the project structure using `summarize_analysis`.
     """

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
    Summarizes the results of file analyses and combines them with the project structure analysis.

    Args:
    analysis_results (List[str]): A list of analysis results for individual files.
    results_structure (str): A summary of the project's overall structure.
    dev_level (str): The developer's proficiency level (e.g., "junior", "mid", "senior").
    description (str): A description of the project or task to guide the summary.

    Returns:
    str: A summarized analysis in text format or JSON format if requested.

    Raises:
    Exception: Logs and re-raises any error that occurs during the summarization process.

    Workflow:
    1. Check if there are any results to summarize. Return a message if none exist.
    2. If the number of results is below the batch size, directly summarize them using `analyze_summary`.
    3. For larger result sets:
        - Break the results into smaller batches for incremental reduction using `analyze_reduce`.
        - Perform batch reductions until the results fit into a single batch.
    4. Return the final summarized reduction.
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


def repo_url_to_git_api_url(input_url: str) -> str | None:
    """
    Converts a GitHub repository URL to its corresponding GitHub API URL.

    Args:
    input_url (str): The URL of the GitHub repository, typically in the form "https://github.com/{owner}/{repo}".

    Returns:
    str | None: The GitHub API URL for accessing the repository's contents if the input URL is valid.
    Returns `None` if the input URL is not a valid GitHub repository link.

    Workflow:
    1. Normalize the input URL by stripping whitespace and converting it to lowercase.
    2. Check if the input URL starts with the predefined GitHub root URL (`GITHUB_ROOT`).
    3. Extract the owner and repository name from the URL.
    4. Construct the API URL using `GITHUB_API_URL` for accessing the repository's contents.
    """
    input_url = input_url.strip().lower()
    if input_url.startswith(GITHUB_ROOT):
        res = input_url.removeprefix(GITHUB_ROOT).split("/")
        if len(res) > 1 and res[0].strip() and res[1].strip():
            owner, repo = res[0].strip(), res[1].strip()
            return f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents"
    return None


async def get_all_files(url: str, client: httpx.AsyncClient) -> Dict[str, Optional[str]] | None:
    """
    Fetches and returns a dictionary of file names and their contents from a given GitHub repository URL.

    Args:
    url (str): The GitHub API URL to fetch the repository's file data.
    client (httpx.AsyncClient): An asynchronous HTTP client for making requests.

    Returns:
    Dict[str, Optional[str]] | None:
    - A dictionary where keys are file names and values are their respective text content
      if they have valid extensions (defined by `VALID_EXTENSIONS`).
    - For files with invalid extensions, their value is `None`.
    - Returns `None` if the request or processing fails.

    Workflow:
    1. Sends a GET request to the provided URL to retrieve repository data.
    2. Parses the JSON response to determine the type of each item (file or directory).
    3. Downloads and stores the content of files with valid extensions in the result dictionary.
    4. Recursively processes directories to fetch their contents.
    5. Logs and handles exceptions for HTTP requests, JSON parsing, and file fetching.

    Notes:
    - The function ignores files with extensions not in the `VALID_EXTENSIONS` set.
    - Files in nested directories are recursively fetched and included in the dictionary.
    - If an error occurs (e.g., a request fails or JSON parsing fails), the function logs the error and returns `None`.
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
