"""Explicit Pydantic input schemas for the MewHelp business tools."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class _NormalizedTextInput(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class QueryOrderInput(_NormalizedTextInput):
    order_no: str = Field(min_length=1, max_length=64)


class QueryProductInput(_NormalizedTextInput):
    product_id: str = Field(min_length=1, max_length=64)


class QueryLogisticsInput(_NormalizedTextInput):
    order_no: str = Field(min_length=1, max_length=64)


class QueryFaqInput(_NormalizedTextInput):
    keyword: str = Field(min_length=1, max_length=128)


class CreateTicketInput(_NormalizedTextInput):
    conversation_id: int = Field(gt=0)
    description: str = Field(min_length=1, max_length=2000)
    ticket_type: Literal["售后", "投诉", "咨询"]
