from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models, schemas
from app.llm_agent import extract_expense
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ChatExpenseRequest(BaseModel):
    text: str


@router.post("/add-expense", response_model=schemas.ExpenseOut)
def add_expense(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    db_expense = models.Expense(**expense.dict())
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


@router.post("/chat-expense", response_model=schemas.ExpenseOut)
def add_expense_via_chat(request: ChatExpenseRequest, db: Session = Depends(get_db)):
    parsed = extract_expense(request.text)
    if not parsed or "amount" not in parsed or "category" not in parsed:
        raise HTTPException(
            status_code=422, detail="Could not understand your expense input"
        )

    db_expense = models.Expense(**parsed)
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


@router.get("/")
def welcome(db: Session = Depends(get_db)):
    return {"message": "Welcome to ZenSpend API"}


@router.get("/expenses", response_model=list[schemas.ExpenseOut])
def get_expenses(db: Session = Depends(get_db)):
    expenses = db.query(models.Expense).order_by(models.Expense.date.desc()).all()
    return expenses
