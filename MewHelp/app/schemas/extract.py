from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RequestType = Literal["refund", "exchange", "repair", "complaint", "other"]


class ExtractRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1)


class AfterSalesTicket(BaseModel):
    order_id: str | None
    request_type: RequestType
    expected_solution: str | None
