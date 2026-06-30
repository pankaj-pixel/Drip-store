from pydantic import BaseModel
from typing import Optional


class Reel(BaseModel):
    id: int
    video: str
    instagram_url: str = ""
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    caption: str
    created_at: str
