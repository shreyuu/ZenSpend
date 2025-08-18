from fastapi import APIRouter, Depends, Body, HTTPException
from langchain_ollama import ChatOllama
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models, schemas
from app.llm_agent import extract_expense, test_agent_with_simple_query
from pydantic import BaseModel
from typing import Optional, List
from langchain.chains import RetrievalQA
from app.memory import vectorstore
from .llm_agent import get_llm_response
import logging

logger = logging.getLogger("api_routes")

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ChatExpenseRequest(BaseModel):
    text: str


class DebugRequest(BaseModel):
    query: str


@router.post("/ask")
def ask_expense_agent(payload: dict):
    user_input = payload.get("message")
    if not user_input:
        raise HTTPException(status_code=400, detail="Message not found")

    logger.info(f"API request: /ask with message: {user_input[:50]}...")
    response = get_llm_response(user_input)
    return {"response": response}


@router.post("/debug/test-agent")
def debug_agent(request: DebugRequest):
    """Endpoint for testing agent behavior with a specific query."""
    logger.info(f"Debug request with query: {request.query}")
    response = test_agent_with_simple_query(request.query)
    return {"query": request.query, "response": response}


@router.post("/debug/test-parser")
def debug_parser(request: DebugRequest):
    """Endpoint for testing expense extraction with a specific query."""
    logger.info(f"Debug parser request with query: {request.query}")
    parsed = extract_expense(request.query)
    return {"query": request.query, "parsed": parsed}


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


@router.post("/semantic-search/")
def search_expenses(query: str):
    retriever = vectorstore.as_retriever()
    qa = RetrievalQA.from_chain_type(
        # llm=ChatOllama(model="llama3.1:8b"),
        llm=ChatOllama(model="phi3:mini"),  # Use a smaller model for testing
        retriever=retriever,
    )
    answer = qa.run(query)
    return {"response": answer}
