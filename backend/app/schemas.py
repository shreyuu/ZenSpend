from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ExpenseCreate(BaseModel):
    amount: float
    category: str
    note: Optional[str] = None


class ExpenseOut(ExpenseCreate):
    id: int
    date: datetime

    class Config:
        orm_mode = True
