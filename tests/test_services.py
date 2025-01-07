import pytest
from httpx import AsyncClient

from config import config
from services import repo_url_to_git_api_url, get_all_files


GITHUB_ROOT = config.get("services", "github_root", fallback="https://github.com/")
GITHUB_API_URL = config.get("services", "github_api_url", fallback="https://api.github.com")
VALID_EXTENSIONS = {".py", ".md", ".ini"}  # Change to the required ones


@pytest.fixture
def httpx_mock(httpx_mock):
    httpx_mock.allow_unused_requests = True
    return httpx_mock


@pytest.mark.parametrize("input_url, expected", [
    # Valid URL
    (f"{GITHUB_ROOT}owner/repo", f"{GITHUB_API_URL}/repos/owner/repo/contents"),
    # Valid URL with uppercase letters (test lower())
    (f"{GITHUB_ROOT}OWNER/REPO", f"{GITHUB_API_URL}/repos/owner/repo/contents"),
    # Valid URL with spaces (test strip())
    (f"  {GITHUB_ROOT}owner/repo  ", f"{GITHUB_API_URL}/repos/owner/repo/contents"),
    # Incomplete URL
    (f"{GITHUB_ROOT}owner/", None),
    # URL, that does not start with GITHUB_ROOT
    ("https://gitlab.com/owner/repo", None),
    # Empty URL
    ("", None),
    # Not a URL
    ("not-a-url", None),
])
def test_repo_url_to_git_api_url(input_url, expected):
    """
    Test function repo_url_to_git_api_url on various data.
    """
    assert repo_url_to_git_api_url(input_url) == expected


@pytest.mark.asyncio
async def test_get_all_files_success(httpx_mock):
    # Mock for root request
    root_url = "https://api.github.com/repos/user/repo/contents"
    httpx_mock.add_response(
        url=root_url,
        json=[
            {"type": "file", "path": "file1.py", "download_url": "https://mock.file1.py"},
            {"type": "file", "path": "file2.md", "download_url": "https://mock.file2.md"},
            {"type": "dir", "path": "subdir", "_links": {"self": "https://mock.subdir"}}
        ],
    )
    # Mock for files downloading
    httpx_mock.add_response(url="https://mock.file1.py", text="print('hello world')")
    httpx_mock.add_response(url="https://mock.file2.md", text="# Markdown content")
    # Mock for folder
    httpx_mock.add_response(
        url="https://mock.subdir",
        json=[
            {"type": "file", "path": "subdir/file3.ini", "download_url": "https://mock.file3.ini"}
        ],
    )
    httpx_mock.add_response(url="https://mock.file3.ini", text="[config]\nkey=value")

    # Test
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
    # Mock for file with not valid extension
    root_url = "https://api.github.com/repos/user/repo/contents"
    httpx_mock.add_response(
        url=root_url,
        json=[
            {"type": "file", "path": "file1.txt", "download_url": "https://mock.file1.txt"}
        ],
    )
    async with AsyncClient() as client:
        result = await get_all_files(root_url, client)

    expected = {"file1.txt": None}  # None for not valid extension
    assert result == expected


@pytest.mark.asyncio
async def test_get_all_files_request_error(httpx_mock):
    # Mock for exception raising
    root_url = "https://api.github.com/repos/user/repo/contents"
    httpx_mock.add_exception(url=root_url, exception=Exception("Request failed"))

    async with AsyncClient() as client:
        result = await get_all_files(root_url, client)

    assert result is None  # None for raise an exception
