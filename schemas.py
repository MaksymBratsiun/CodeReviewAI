from typing import Literal

from pydantic import BaseModel


class ReviewRequest(BaseModel):
    description: str
    git_url: str = "https://github.com/owner/repository"
    dev_level: Literal["junior", "middle", "strong"] = "junior"
