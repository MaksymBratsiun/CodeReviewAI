# CodeReviewAI

# Task

Auto-Review Tool.

 In this assignment, your goal is to create a backend prototype for a Coding Assignment Auto-Review Tool using Python. 
 This tool will help automate the process of reviewing coding assignments by leveraging OpenAi's GPT API (or alternative) 
 for code analysis and the GitHub API for repository access.

# Requirements
- Python 3.x
- Fast API
- Open AI API
- Other dependencies (install using `pip install -r requirements.txt`)

# Usage
- update project from Git
- create virtual environment
- install requirements
```bash
pip install -r requirements.txt
```
- create '.env' with OpenAI KEY according 'example.env'
- run server
```bash
uvicorn main:app --host localhost --port 8000 --reload
```
- open 'http://localhost:8000/docs#' in a web browser
- make post like
```{
  "description": "assigment_description ",
  "git_url": "https://github.com/MaksymBratsiun/CodeReviewAI",
  "dev_level": "junior"
}
```
- response
```
{  "comments": "Downsides:  1. The project shows redundancy in dependency management tools and lacks automated testing, 
which is essential for maintaining code quality.2. The `ReviewRequest` model in `main.py` uses defaults that may 
not be universally applicable, suggesting a need for more flexible design practices.3. Error handling in `services.py`
is insufficient, particularly in functions interacting with external APIs, which could lead to runtime errors or 
unhandled exceptions. ",
  "rating": "3",
  "conclusion": ":  The developer demonstrates a good understanding of Python and FastAPI framework but needs to focus 
  on robust error handling, eliminate redundancy, and include comprehensive documentation to improve maintainability 
  and usability of the code.",
  "project_structure": [
    ".gitignore",
    "LICENSE",
    "README.md",
    "example.env",
    "main.py",
    "poetry.lock",
    "pyproject.toml",
    "requirements.txt",
    "schemas.py",
    "services.py"
  ]
}
```