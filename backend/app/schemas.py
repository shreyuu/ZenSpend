from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from datetime import date


class ExpenseCreate(BaseModel):
    amount: float
    category: str
    date: date
    description: Optional[str] = None


class ExpenseQuery(BaseModel):
    start_date: date
    end_date: date
    category: Optional[str] = None


class ExpenseOut(ExpenseCreate):
    id: int
    date: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )
