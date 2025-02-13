import os
import time
import logging
import json

import openai
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from config import APP_NAME, DEBUG_LEVEL, RESPONSE_REQUIRED_KEYS
from schemas import ReviewRequest
from services import repo_url_to_git_api_url, get_all_files, perform_analysis


load_dotenv()
openai.api_key = os.environ.get('OPENAI_API_KEY')

# APP_NAME = config.get("general", "app_name", fallback="CodeReviewAI")
# DEBUG_LEVEL = config.get("general", "debug", fallback="INFO")
# RESPONSE_REQUIRED_KEYS = {"Comment", "Skills", "Rating"}


logging.basicConfig(level=DEBUG_LEVEL)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Initialization FastAPI
app = FastAPI()


@app.post("/review")
async def review(request: ReviewRequest) -> JSONResponse:
    """
    Endpoint to review and analyze a Git repository.

    This function processes an incoming POST request to review a Git repository by analyzing its structure and files.
    It uses the OpenAI API to perform various analyses, validates the results, and returns structured feedback in JSON.

    Args:
    request (ReviewRequest): The request body containing:
    - git_url (str): URL of the Git repository to analyze.
    - dev_level (str): The developer's proficiency level for contextual analysis.
    - description (str): Description or context for the analysis.

    Returns:
    JSONResponse: A JSON object with the analyzed results containing keys:
    - "Comment" (str): General comments about the repository and developer's code.
    - "Skills" (str): Observations on the developer's skills.
    - "Rating" (int): A numeric rating (1-5) for the developer's performance.

    Raises:
    HTTPException:
    - 404: If the repository URL is invalid or no files are found.
    - 422: Validation error if missing required keys during file analyze.
    - 500: For errors in processing, such as invalid JSON, missing required keys, or unhandled exceptions.
    - 503: HTTP request files downloading failed.
    - 504: Repository request files downloading timeout.

    Process:
    1. Validate the Git repository URL and retrieve the repository's API URL.
    2. Fetch all files from the repository.
    3. Perform an analysis on the retrieved files using the OpenAI API.
    4. Parse and validate the analysis result to ensure required keys are present.
    5. Return the validated result as a structured JSON response.

    Logging:
    - Logs significant steps, including start/end times, errors, and validation results, for monitoring and debugging.
    """

    logger.info(f"Start {APP_NAME}")
    start_time = time.time()
    git_api_url = repo_url_to_git_api_url(request.git_url)

    if not git_api_url:
        raise HTTPException(status_code=404, detail="Incorrect repository url")

    try:
        # Files downloading
        async with httpx.AsyncClient() as client:
            try:
                # Files downloading
                files = await get_all_files(git_api_url, client)
                if not files:
                    raise HTTPException(status_code=404, detail="Repository, branch or valid files not found.")
            except httpx.TimeoutException as e:
                logger.error(f"HTTP request timed out: {e}")
                raise HTTPException(status_code=504, detail="Repository request timeout.")
            except httpx.RequestError as e:
                logger.error(f"HTTP request failed: {e}")
                raise HTTPException(status_code=503, detail="Error communicating with Git repository.")

        # Analyze
        try:
            # Perform analysis
            analysis_result = await perform_analysis(files, request.dev_level, request.description)

            # Validate and parse response
            logger.info(f"Parsing and validating analysis result")
            response_data = json.loads(analysis_result)

            # Ensure required keys exist
            required_keys = RESPONSE_REQUIRED_KEYS
            missing_keys = required_keys - response_data.keys()
            if missing_keys:
                logger.error(f"Final response is missing required keys: {missing_keys}")
                raise HTTPException(status_code=422, detail=f"Missing required keys: {missing_keys}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format in analysis result: {e}")
            raise HTTPException(status_code=500, detail="Invalid JSON format in response from analysis.")
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise HTTPException(status_code=422, detail=str(e))
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
