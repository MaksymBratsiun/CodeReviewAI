import os
import time
import logging
import json

import openai
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from config import config
from schemas import ReviewRequest
from services import repo_url_to_git_api_url, get_all_files, perform_analysis


load_dotenv()
openai.api_key = os.environ.get('OPENAI_API_KEY')

APP_NAME = config.get("general", "app_name", fallback="CodeReviewAI")

DEBUG_LEVEL = config.get("general", "debug", fallback="INFO")
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

level = LOG_LEVELS.get(DEBUG_LEVEL.upper(), logging.INFO)
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Initialization FastAPI
app = FastAPI()


@app.post("/review")
async def review(request: ReviewRequest) -> JSONResponse:
    """
    Handles the review process for a given Git repository.

    This endpoint takes in details of a Git repository, fetches its files,
    and performs an analysis based on the provided development level and description.

    Args:
        request (ReviewRequest): The request payload containing:
            - `git_url` (str): The URL of the Git repository to analyze.
            - `dev_level` (str): The development level for the analysis.
            - `description` (str): Additional context or description for the analysis.

    Returns:
        JSONResponse: A JSON object containing the analysis results.

    Raises:
        HTTPException:
            - If the Git repository URL is invalid (404).
            - If the repository or branch is not found (404).
            - For any unhandled internal errors (500).

    Process:
        1. Validate the provided `git_url` and convert it to an API-compatible URL.
        2. Fetch all files from the repository asynchronously using `httpx.AsyncClient`.
        3. Perform a detailed analysis of the files:
            - Analyze the structure and content.
            - Generate a summarized review based on the development level and description.
        4. Return the analysis result as a JSON response.

    Logging:
        - Logs the start and end of the review process.
        - Logs any HTTP or unhandled exceptions.

    Notes:
        - The function uses `httpx.AsyncClient` for asynchronous HTTP operations.
        - Analysis is delegated to the `perform_analysis` function.
    """

    logger.info(f"Start {APP_NAME}")
    start_time = time.time()
    git_api_url = repo_url_to_git_api_url(request.git_url)

    if not git_api_url:
        raise HTTPException(status_code=404, detail="Incorrect repository url")

    try:
        async with httpx.AsyncClient() as client:
            # Files downloading
            files = await get_all_files(git_api_url, client)
            if not files:
                raise HTTPException(status_code=404, detail="Repository or branch not found")

        # Analyze
        try:
            # Perform analysis
            analysis_result = await perform_analysis(files, request.dev_level, request.description)

            # Validate and parse response
            logger.info(f"Parsing and validating analysis result")
            response_data = json.loads(analysis_result)

            # Ensure required keys exist
            required_keys = {"Comment", "Skills", "Rating"}
            missing_keys = required_keys - response_data.keys()
            if missing_keys:
                logger.error(f"Final response is missing required keys: {missing_keys}")
                raise ValueError(f"Missing required keys: {missing_keys}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format in analysis result: {e}")
            raise HTTPException(status_code=500, detail="Invalid JSON format in response from analysis.")
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            logger.exception(f"Unhandled error occurred during analysis: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

        # Return the validated response as JSON
        logger.info(f"Review finished in {time.time() - start_time:.2f}s")
        return JSONResponse(content=response_data)

    except HTTPException as http_err:
        logger.error(f"HTTP error: {http_err.detail}")
        raise
    except Exception as e:
        logger.exception(f"Unhandled error occurred during review: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
