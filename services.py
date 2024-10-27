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


def result_dividing(input_string : str) -> dict:
    res = input_string.replace("\n", "").replace("#", " ").replace("*", " ").strip()
    split_result_rating = res.split("Rating")
    comments, split_result = split_result_rating[0].strip(), split_result_rating[1:]
    split_result_level = split_result[0].split("level")
    rating, split_result = split_result_level[0].strip(), split_result_level[1:]

    for i in rating:
        if i.isdigit():
            rating = i
            break

    split_result_conclusion = split_result[0].split("Conclusion")
    split_result, conclusion = split_result_conclusion[0].strip(), split_result_conclusion[1:][0]
    comments = f"{comments} {split_result}"

    return {"comments": comments, "rating": rating, "conclusion": conclusion}
