# CodeReviewAI

# Task

Auto-Review Tool.

 Create tool will help automate the process of reviewing coding assignments by leveraging OpenAi's GPT API
 for code analysis and the GitHub API for repository access.

Endpoint Specification:
POST/review
Accept the following data in the request body:
- description: string (description of the coding assignment)
- git_url: string (URL of the GitHub repository to review)
- dev_level: string (candidate level: Junior, Middle, or Senior)

The endpoint should:
1. Use the GitHub API to fetch the repository contents.
2. Use OpenAl's GPT API to analyze the code and generate a review.
3. Return the review result (text) in the following format: Found files, Downsides/Comments, Rating,

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
  "description": "short and simple",
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