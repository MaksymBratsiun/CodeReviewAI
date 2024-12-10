import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient

from config import config
from services import repo_url_to_git_api_url, get_all_files


GITHUB_ROOT = config.get("services", "github_root", fallback="https://github.com/")
GITHUB_API_URL = config.get("services", "github_api_url", fallback="https://api.github.com")
VALID_EXTENSIONS = {".py", ".md", ".ini"}  # Можете змінити на відповідні значення


@pytest.mark.parametrize("input_url, expected", [
    # Валідний URL
    (f"{GITHUB_ROOT}owner/repo", f"{GITHUB_API_URL}/repos/owner/repo/contents"),
    # Валідний URL з великими літерами (перевірка lower())
    (f"{GITHUB_ROOT}OWNER/REPO", f"{GITHUB_API_URL}/repos/owner/repo/contents"),
    # Валідний URL з пробілами (перевірка strip())
    (f"  {GITHUB_ROOT}owner/repo  ", f"{GITHUB_API_URL}/repos/owner/repo/contents"),
    # Неповний URL
    (f"{GITHUB_ROOT}owner/", None),
    # URL, який не починається з GITHUB_ROOT
    ("https://gitlab.com/owner/repo", None),
    # Порожній рядок
    ("", None),
    # Рядок без схожості на URL
    ("not-a-url", None),
])
def test_repo_url_to_git_api_url(input_url, expected):
    """
    Тестуємо функцію repo_url_to_git_api_url з різними вхідними даними.
    """
    assert repo_url_to_git_api_url(input_url) == expected

@pytest.mark.asyncio
async def test_get_all_files_success(httpx_mock):
    # Мок для кореневого запиту
    root_url = "https://api.github.com/repos/user/repo/contents"
    httpx_mock.add_response(
        url=root_url,
        json=[
            {"type": "file", "path": "file1.py", "download_url": "https://mock.file1.py"},
            {"type": "file", "path": "file2.md", "download_url": "https://mock.file2.md"},
            {"type": "dir", "path": "subdir", "_links": {"self": "https://mock.subdir"}}
        ],
    )
    # Мок для завантаження файлів
    httpx_mock.add_response(url="https://mock.file1.py", text="print('hello world')")
    httpx_mock.add_response(url="https://mock.file2.md", text="# Markdown content")
    # Мок для папки
    httpx_mock.add_response(
        url="https://mock.subdir",
        json=[
            {"type": "file", "path": "subdir/file3.ini", "download_url": "https://mock.file3.ini"}
        ],
    )
    httpx_mock.add_response(url="https://mock.file3.ini", text="[config]\nkey=value")

    # Тестування
    async with AsyncClient() as client:
        result = await get_all_files(root_url, client)

    expected = {
        "file1.py": "print('hello world')",
        "file2.md": "# Markdown content",
        "subdir/file3.ini": "[config]\nkey=value",
    }
    assert result == expected

@pytest.mark.asyncio
async def test_get_all_files_invalid_extension(httpx_mock):
    # Мок для файлів з невірним розширенням
    root_url = "https://api.github.com/repos/user/repo/contents"
    httpx_mock.add_response(
        url=root_url,
        json=[
            {"type": "file", "path": "file1.txt", "download_url": "https://mock.file1.txt"}
        ],
    )
    # Мок для завантаження файлу
    httpx_mock.add_response(url="https://mock.file1.txt", text="This is a text file")

    async with AsyncClient() as client:
        result = await get_all_files(root_url, client)

    expected = {"file1.txt": None}  # Очікуємо None для невірного розширення
    assert result == expected


@pytest.mark.asyncio
async def test_get_all_files_request_error(httpx_mock):
    # Мок для виклику з помилкою
    root_url = "https://api.github.com/repos/user/repo/contents"
    httpx_mock.add_exception(url=root_url, exception=Exception("Request failed"))

    async with AsyncClient() as client:
        result = await get_all_files(root_url, client)

    assert result is None  # Очікуємо None у разі помилки