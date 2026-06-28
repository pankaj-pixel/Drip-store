import json
from typing import List

from pydantic import BaseModel, field_validator


class Product(BaseModel):
    id: int
    name: str
    category: str
    price: int  # paise
    sizes: List[str]
    image: str
    description: str
    in_stock: bool

    @field_validator("sizes", mode="before")
    @classmethod
    def parse_sizes(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
