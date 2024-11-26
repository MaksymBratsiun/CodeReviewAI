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
**Solutions:**
1. Enhance error handling and improve flexibility in design practices.
2. Consolidate dependency management by choosing one package manager and organize modules for better maintainability.
**Skills:**
The developer demonstrates a good understanding of Python, FastAPI, and asynchronous programming, but could focus on 
refining error handling and code documentation for better quality and maintainability.
**Rating:** 
3 out of 5 for developer level: junior
```