import os

from fastapi import FastAPI, HTTPException
from openai import OpenAI
import requests
from dotenv import load_dotenv

load_dotenv()

USER_NAME = "MaksymBratsiun"
REPO = "homework7"

TEST_URL = "https://github.com/MaksymBratsiun/NER_BERT/blob/main/inference_NER.py"

app = FastAPI()

GITHUB_API_URL = "https://api.github.com"

file_content = """
from setuptools import setup, find_namespace_packages

setup(
    name='clean_folder',
    version='1.0.0',
    description='Clean folder and sort',
    url='https://github.com/MaksymBratsiun/homework7',
    author='Maksym Bratsiun',
    license='MIT',
    packages=find_namespace_packages(),
    entry_points={'console_scripts': ['clean-folder=clean_folder.clean:main']}
)
"""

@app.get("/api/healthchecker")
def healthchecker():
    return {"message": "OK"}


@app.get("/analyze_repo")
async def analyze_repo(target_url: str, branch: str = "main"):
    contents_url = f"{GITHUB_API_URL}/repos/{USER_NAME}/{REPO}/contents"
    response = requests.get(contents_url, params={"ref": branch})

    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Repository not found or could not be accessed")

    files_data = response.json()
    files_map = []
    analysis_results = []

    def read_files(files):
        for file_info in files:
            if file_info['type'] == 'file':
                file_response = requests.get(file_info['download_url'])
                if file_response.status_code == 200:
                    analysis_results.append(file_response.text)

                    # # Надсилаємо вміст файлу в OpenAI для аналізу
                    # try:
                    #     response = openai.ChatCompletion.create(
                    #         model="gpt-3.5-turbo",
                    #         messages=[
                    #             {"role": "system", "content": "You are analyzing a code file."},
                    #             {"role": "user", "content": file_content}
                    #         ]
                    #     )
                    #     analysis_results.append({
                    #         "file": file_info['path'],
                    #         "analysis": response.choices[0].message['content']
                    #     })
                    # except Exception as e:
                    #     analysis_results.append({
                    #         "file": file_info['path'],
                    #         "error": str(e)
                    #     })
            elif file_info['type'] == 'dir':

                subdir_response = requests.get(file_info['_links']['self'])
                if subdir_response.status_code == 200:
                    read_files(subdir_response.json())

    read_files(files_data)
    print("files", len(analysis_results))
    return analysis_results


@app.get("/open_api_test")
def open_api_test():
    analysis_results = []
    client = OpenAI(api_key=os.environ.get('OPEN_AI_API_KEY'))
    grade = "junior"

    try:
        response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system",
                     "content": f"You are an experienced software reviewer, specialized in assessing code quality "
                                f"for {grade} level developer. "
                                f"Please evaluate the code, identifying weaknesses and issues, and give feedback. "
                                f"Rate the code on a scale from 1 to 5 based on the {grade} developer level. "
                                f"provide a brief comment on the developer's skill level and include suggestions"
                                f" for improvement."
                     },
                    {"role": "user",
                     "content": (f"{file_content}"
                                 f"Downsides: identifying weaknesses and issues."
                                 f"Please evaluate the code as a {grade}-level submission rate it on a scale of 1 to 5,"
                                 f"like:'Rating 3/5 (for {grade} level)' in ne line. "
                                 f"Comments: write a brief comment on the developer’s skills."
                                 )}
                ],
                max_tokens=500,
                temperature=0.8
            )
        analysis_results.append({"analysis": response.choices})
    except Exception as e:
        analysis_results.append({"error": str(e)})

    return analysis_results


