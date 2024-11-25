import os
import json
import time

import openai
import httpx
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException


from schemas import ReviewRequest
from services import repo_url_to_git_api_url, get_all_files
from services import analyze_summary, analyze_structure, analyze_file_content, analyze_reduce

BRANCH = "main"
GPT_MODEL = "gpt-3.5-turbo"
MAX_TOKEN = 300
MAX_TOKEN_SUMMARY = 500
TEMPERATURE = 0.6
BATCH_SIZE = 7


load_dotenv()
openai.api_key = os.environ.get('OPENAI_API_KEY')
app = FastAPI()


@app.post("/review")
async def review(request: ReviewRequest) -> str:  # json dump
    print("Run Main")
    start = time.time()
    git_api_url = repo_url_to_git_api_url(request.git_url)

    if not git_api_url:
        raise HTTPException(status_code=404, detail="Incorrect repository url")

    dev_level = request.dev_level
    description = request.description
    analysis_results = []

    try:
        async with httpx.AsyncClient() as client:
            files = await get_all_files(git_api_url, client)
            if not files:
                raise HTTPException(status_code=404, detail="Repository or branch not found")

            results_structure = analyze_structure(files, description)
            print("Structure analyze done", results_structure)
            cleaned_files = {file_path: content for file_path, content in files.items() if content is not None}
            analysis_tasks = [analyze_file_content(name, content, dev_level, description)
                              for name, content in cleaned_files.items()]
            print("File analyze done. Files:", len(cleaned_files.keys()))
            analysis_results = await asyncio.gather(*analysis_tasks)

        if len(analysis_results) == 0:
            analysis_results = "No file content to analyze."
        elif len(analysis_results) <= 7:
            print("Summary starts, batch less 7")
            analysis_results = await analyze_summary(analysis_results, results_structure, dev_level, description)
        else:
            print("Summary starts, batch more 7", len(analysis_results), type(analysis_results))
            analysis_results.append(results_structure)
            print("Summary list_strings", len(analysis_results), type(analysis_results))
            while len(analysis_results) >= BATCH_SIZE:
                print("Reduce starts. Strings:", len(analysis_results))
                tasks = []
                for i in range(0, len(analysis_results), BATCH_SIZE):
                    print(i)
                    batch = analysis_results[i:i + BATCH_SIZE]
                    tasks.append(analyze_reduce(batch, dev_level, description))
                analysis_results = [await future for future in asyncio.as_completed(tasks)]
                # analysis_results = await asyncio.gather(*tasks)
                print("while loop ends")

            if type(analysis_results) == list:
                analysis_results = await analyze_reduce(analysis_results, dev_level, description)
            else:
                analysis_results = "Something wrong"

        print("Time run: ", time.time() - start)
        return json.dumps(analysis_results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
