import os
import time
import logging

import openai
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from schemas import ReviewRequest
from services import repo_url_to_git_api_url, get_all_files
from services import perform_analysis

BRANCH = "main"
GPT_MODEL = "gpt-3.5-turbo"
MAX_TOKEN = 300
MAX_TOKEN_SUMMARY = 500
TEMPERATURE = 0.6
BATCH_SIZE = 7


load_dotenv()
openai.api_key = os.environ.get('OPENAI_API_KEY')

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

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

    logger.info(f"Start review")
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
            analysis_result = await perform_analysis(files, request.dev_level, request.description)

        logger.info(f"Review finished in {time.time() - start_time:.2f}s")
        return JSONResponse(content={"result": analysis_result})

    except HTTPException as http_err:
        logger.error(f"HTTP error: {http_err.detail}")
        raise
    except Exception as e:
        logger.exception(f"Unhandled error occurred during review: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
