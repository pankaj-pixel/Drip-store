import json
from typing import List

from pydantic import BaseModel, field_validator


class OrderItem(BaseModel):
    product_id: int
    name: str
    size: str
    qty: int
    price: int  # paise per unit


class Order(BaseModel):
    id: int | None = None
    customer_name: str
    phone: str
    address: str
    items: List[OrderItem]
    total: int  # paise
    whatsapp_sent: bool = False
    created_at: str | None = None

    @field_validator("items", mode="before")
    @classmethod
    def parse_items(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
