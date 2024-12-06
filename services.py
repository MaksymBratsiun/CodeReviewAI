import logging
import configparser
from typing import Dict, Optional, List

import httpx
import asyncio

from config import config
from api_requests import analyze_summary, analyze_reduce, analyze_structure, analyze_file_content

GITHUB_ROOT = config.get("services", "github_root", fallback="https://github.com/")
GITHUB_API_URL = config.get("services", "github_api_url", fallback="https://api.github.com")
BATCH_SIZE = config.getint("services", "butch_size", fallback=7)

DEFAULT_VALID_EXTENSIONS = {".py", ".md", ".ini"}  # Default valid file extensions
try:
    VALID_EXTENSIONS = set(config.get("services", "valid_extensions").split(","))
except configparser.NoSectionError:
    logging.error("Config section 'services' not found in config.ini. Using default VALID_EXTENSIONS.")
    VALID_EXTENSIONS = DEFAULT_VALID_EXTENSIONS
except configparser.NoOptionError:
    logging.error("Option 'valid_extensions' not found in section 'services'. Using default VALID_EXTENSIONS.")
    VALID_EXTENSIONS = DEFAULT_VALID_EXTENSIONS

logger = logging.getLogger(__name__)


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
