import pytest
import os
from unittest.mock import patch, Mock, call
from dotenv import load_dotenv
import openai

from api_requests import analyze_structure
from config import config

GPT_MODEL = config.get("api_requests", "model", fallback="gpt-3.5-turbo")
MAX_TOKENS = config.getint("api_requests", "max_tokens", fallback=400)
MAX_TOKEN_SUMMARY = config.getint("api_requests", "max_token_summary", fallback=500)
TEMPERATURE = config.getfloat("api_requests", "temperature", fallback=0.6)

# f"{PROMPT_SYS}{description}"
PROMPT_SYS = config.get("api_requests", "prompt_sys_json", fallback="Evaluate the code according:")

# f"Project structure:{structure}{PROMPT...}"
PROMPT_USER_STRUCTURE = config.get("api_requests", "prompt_user_structure", fallback="Evaluate the code according:")

# f"File name: {name}\n{content}\n{PROMPT...}{level}"
PROMPT_USER_FILE_ANALYZE = config.get("api_requests", "prompt_user_file_analyze", fallback=" Evaluate the code")

# f"{..SUMMARY_TASK}{summaries_text}{..SUMMARY_SOLUTIONS}\n{..SUMMARY_SKILLS}{..SUMMARY_RATING}{dev_level}"
PROMPT_USER_SUMMARY_TASK = config.get("api_requests", "prompt_user_summary_task",
                                      fallback="Make summary review according preview analyze: ")
PROMPT_USER_SUMMARY_SOLUTIONS = config.get("api_requests", "prompt_user_summary_solutions",
                                           fallback="Solutions: identifying weaknesses and good solutions.")
PROMPT_USER_SUMMARY_SKILLS = config.get("api_requests", "prompt_user_summary_skills",
                                        fallback="Skills: write a brief comment on the developer’s skills.")
PROMPT_USER_SUMMARY_RATING = config.get("api_requests", "prompt_user_summary_rating",
                                        fallback="Rating: (from 1 to 5) for developer level:")

# f"{..REDUCE_TASK}{summaries_text}{..REDUCE_SOLUTIONS}\n{..REDUCE_SKILLS}{..REDUCE_RATING}{dev_level}"
PROMPT_USER_REDUCE_TASK = config.get("api_requests", "prompt_user_reduce_task",
                                     fallback="Make summary review according preview analyze:")
PROMPT_USER_REDUCE_SOLUTIONS = config.get("api_requests", "prompt_user_reduce_solutions",
                                          fallback="Solutions: identifying weaknesses and good solutions.")
PROMPT_USER_REDUCE_SKILLS = config.get("api_requests", "prompt_user_reduce_skills",
                                       fallback="Skills: write a brief comment on the developer’s skills.")
PROMPT_USER_REDUCE_RATING = config.get("api_requests", "prompt_user_reduce_rating",
                                       fallback="Rating: (from 1 to 5) for developer level:")
load_dotenv()
openai.api_key = os.environ.get('OPENAI_API_KEY')


class MockOpenAIResponse:
    """Mock response for OpenAI API."""
    def __init__(self, content: str):
        self.choices = [
            Mock(message=Mock(role="assistant", content=content))
        ]


@pytest.mark.asyncio
@patch("openai.chat.completions.create", new_callable=Mock)
async def test_analyze_structure_valid_response(mock_create):
    # Customization of Mock response
    mock_content = "Mocked response from OpenAI API"
    mock_create.return_value = MockOpenAIResponse(mock_content)

    files = {"file1.txt": "content of file1", "file2.txt": "content of file2"}
    description = "Mock project description"

    # Call tested function
    response = await analyze_structure(files, description)

    # Response check
    assert response == mock_content

    # Check response call
    structure = ", ".join(files.keys())
    mock_create.assert_called_once_with(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": f"{PROMPT_SYS}{description}"},
            {"role": "user", "content": f"Project structure:{structure}\n{PROMPT_USER_STRUCTURE}"},
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )


@pytest.mark.asyncio
@patch("openai.chat.completions.create", new_callable=Mock)
async def test_analyze_structure_with_error(mock_create):
    # Імітація помилки API
    mock_create.side_effect = Exception("Mocked API error")

    files = {"file1.txt": "content of file1", "file2.txt": "content of file2"}
    description = "Mock project description"

    # Виклик функції
    response = await analyze_structure(files, description)

    # Перевірка результату
    assert response == "Error: Unexpected failure in analyze_structure: Mocked API error"
    mock_create.assert_called_once()

