import re

import requests

GITHUB_ROOT = "https://github.com/"
GITHUB_API_URL = "https://api.github.com"


def repo_url_to_git_api_url(input_url: str) -> str | None:

    input_url = input_url.strip().lower()
    if input_url.startswith(GITHUB_ROOT):
        res = input_url.removeprefix(GITHUB_ROOT).split("/")
        if len(res) > 1:
            owner, repo = res[0], res[1]
            return f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents"


def get_all_files(git_response: requests.Response) -> dict:
    files_to_analyze = {}

    def read_files(files):
        for file_info in files:
            if file_info['type'] == 'file':
                if file_info['name'].endswith((".py", ".md", ".ini")):
                    file_response = requests.get(file_info['download_url'])
                    if file_response.status_code == 200:
                        files_to_analyze.update({file_info['path']: file_response.text})
                else:
                    files_to_analyze.update({file_info['path']: None})
            elif file_info['type'] == 'dir':
                subdir_response = requests.get(file_info['_links']['self'])
                if subdir_response.status_code == 200:
                    read_files(subdir_response.json())

    read_files(git_response.json())

    return files_to_analyze


def result_dividing(input_string: str) -> dict:
    comments = None
    rating = 0
    conclusion = None
    res = input_string.replace("\n", "").replace("#", " ").replace("*", " ").strip()

    if res.find("Conclusion") != -1:
        split_result_conclusion = input_string.split("Conclusion")
        comments, conclusion = split_result_conclusion[0], "".join(split_result_conclusion[1:])
        if comments.find("Rating") != 0:
            pattern = rf"{'Rating'}\D*(\d)"
            match = re.search(pattern, comments)
            if match:
                rating = match.group(1)
            else:
                rating = 0
        else:
            pattern = rf"{'Rating'}\D*(\d)"
            match = re.search(pattern, conclusion)
            if match:
                rating = match.group(1)
            else:
                rating = 0
    else:
        comments = input_string
        pattern = rf"{'Rating'}\D*(\d)"
        match = re.search(pattern, comments)
        if match:
            rating = match.group(1)
        else:
            rating = 0

    return {"comments": comments, "rating": rating, "conclusion": conclusion}
