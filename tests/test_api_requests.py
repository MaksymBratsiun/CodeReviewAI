import pytest
import json

from unittest.mock import patch, AsyncMock, Mock
from openai._exceptions import OpenAIError

from api_requests import analyze_structure
from config import GPT_MODEL, MAX_TOKENS, TEMPERATURE
from config import PROMPT_SYS, PROMPT_USER_STRUCTURE, PROMPT_USER_FILE_ANALYZE
from config import PROMPT_USER_SUMMARY_TASK, PROMPT_USER_SUMMARY_SOLUTIONS
from config import PROMPT_USER_SUMMARY_SKILLS, PROMPT_USER_SUMMARY_RATING
from config import PROMPT_USER_REDUCE_TASK, PROMPT_USER_REDUCE_SOLUTIONS
from config import PROMPT_USER_REDUCE_SKILLS, PROMPT_USER_REDUCE_RATING


class MockOpenAIResponse:
    """Mock response for OpenAI API."""
    def __init__(self, content: str):
        self.choices = [
            Mock(message=Mock(role="assistant", content=content))
        ]


@pytest.mark.asyncio
@patch("config.client.chat.completions.create", new_callable=AsyncMock)
async def test_analyze_structure_valid_response(mock_create):
    # Arrange
    mock_data = {
        "Solutions": "Mocked solution",
        "Skills": "Mocked skills",
        "Rating": 2
    }
    mock_content = json.dumps(mock_data)
    mock_create.return_value = MockOpenAIResponse(mock_content)

    files = {"file1.txt": "content of file1", "file2.txt": "content of file2"}
    description = "Mock project description"
    structure = ", ".join(files.keys())

    # Act
    response = await analyze_structure(files, description)

    # Assert
    assert response == mock_content

    mock_create.assert_awaited_once_with(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": f"{PROMPT_SYS}{description}"},
            {"role": "user", "content": f"Project structure:{structure}\n{PROMPT_USER_STRUCTURE}"}
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )


@pytest.mark.asyncio
@patch("config.client.chat.completions.create", new_callable=AsyncMock)
async def test_analyze_structure_openai_error(mock_create):
    # Arrange: OpenAIError handle error
    mock_create.side_effect = OpenAIError("Simulated OpenAI failure")

    files = {"file1.py": "print('Hello')"}
    description = "Test project with error"

    # Act
    response = await analyze_structure(files, description)

    # Assert
    assert "Error: OpenAI API failed with error" in response
    assert "Simulated OpenAI failure" in response


@pytest.mark.asyncio
@patch("config.client.chat.completions.create", new_callable=AsyncMock)
async def test_analyze_structure_unexpected_exception(mock_create):
    # Arrange: Exception handle error
    mock_create.side_effect = Exception("Unexpected test error")

    files = {"file1.py": "print('test')"}
    description = "Some project"

    # Act
    response = await analyze_structure(files, description)

    # Assert
    assert "Error: Unexpected failure in analyze_structure" in response
    assert "Unexpected test error" in response