import os
import json

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
import requests
from openai import OpenAI

from schemas import ReviewRequest
from services import repo_url_to_git_api_url, get_all_files

BRANCH = "main"
GPT_MODEL = "gpt-4-turbo"
MAX_TOKEN = 300
MAX_TOKEN_SUMMARY = 500
TEMPERATURE = 0.7
SYS_CONTENT = ""


load_dotenv()

app = FastAPI()


@app.post("/review")
async def review(request: ReviewRequest):

    git_api_url = repo_url_to_git_api_url(request.git_url)

    if not git_api_url:
        raise HTTPException(status_code=404, detail="Incorrect repository url")

    response = requests.get(git_api_url, params={"ref": "main"})

    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Repository not found or could not be accessed")

    files_to_analyze = get_all_files(response)

    dev_level = request.dev_level
    project_structure = list(files_to_analyze)
    description = request.description

    analysis_results = []
    client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system",
                 "content": f"You are an experienced software reviewer. Evaluate the code according: {description}"
                 },
                {"role": "user",
                 "content": (f"{project_structure} is project structure."
                             f"Identifying weaknesses and issues and good solutions in 3 sentences."
                             f"Make conclusion in 1 sentences."
                             )}
            ],
            max_tokens=MAX_TOKEN,
            temperature=TEMPERATURE
        )
        analysis_results.append(response.choices[0].message.content.strip())
    except Exception as e:
        analysis_results.append({"error": str(e)})

    count_useful_files = 0
    for file_name, file_content in files_to_analyze.items():
        if file_content:
            count_useful_files += 1
            try:
                response = client.chat.completions.create(
                    model=GPT_MODEL,
                    messages=[
                        {"role": "system",
                         "content": f"You are an experienced software reviewer.Evaluate code according: {description}"
                         },
                        {"role": "user",
                         "content": (f"File name: '{file_name}'"
                                     f"{file_content}"
                                     f"Downsides: identifying weaknesses and issues and good solutions in 3 sentences."
                                     f"Conclusion: write a brief comment on the developer’s skills in 1 sentence."
                                     )}
                    ],
                    max_tokens=MAX_TOKEN,
                    temperature=TEMPERATURE
                )
                analysis_results.append(response.choices[0].message.content.strip())
                if count_useful_files % 15 == 0:
                    structure_data, files_data = analysis_results[0], analysis_results[1:]
                    response = client.chat.completions.create(
                        model=GPT_MODEL,
                        messages=[
                            {"role": "system",
                             "content": f"You are experienced software reviewer.Evaluate code according:{description}"
                             },
                            {"role": "user",
                             "content": f"Make summary review according preview analyze: {files_data}"}
                        ],
                        max_tokens=MAX_TOKEN,
                        temperature=TEMPERATURE
                    )
                    analysis_results = [structure_data, response.choices[0].message.content.strip()]
            except Exception as e:
                analysis_results.append({"error": str(e)})

    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system",
                 "content": f"You are an experienced software reviewer.Evaluate the code according: {description}"
                 },
                {"role": "user",
                 "content": (f"Make summary review according preview analyze: {analysis_results}"
                             f"Downsides: identifying weaknesses and issues and good solutions in 3 sentences."
                             f"Rating: (from 1 to 5, like 3/5) for {dev_level} level."
                             f"Conclusion: write a brief comment on the developer’s skills in 1 sentence."
                             )}
            ],
            max_tokens=MAX_TOKEN_SUMMARY,
            temperature=TEMPERATURE
        )
        summary_result = response.choices[0].message.content.strip()
    except Exception as e:
        summary_result = {"error": str(e)}

    return [project_structure, summary_result]
