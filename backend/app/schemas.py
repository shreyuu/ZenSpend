from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ExpenseCreate(BaseModel):
    amount: float
    category: str
    note: Optional[str] = None


class ExpenseOut(ExpenseCreate):
    id: int
    date: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
