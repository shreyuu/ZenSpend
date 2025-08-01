from numbers import Real
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.database import engine
from app import models
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from langchain.tools import tool

from app.schemas import ExpenseCreate

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="ZenSpend API")

models.Base.metadata.create_all(bind=engine)

# Database connection
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor(cursor_factory=RealDictCursor)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.post("/expenses/add")
def add_expense(data: ExpenseCreate):
    cur.execute(
        "INSERT INTO expenses (amount, category, date, description) VALUES (%s, %s, %s, %s)",
        (data.amount, data.category, data.date, data.description),
    )
    conn.commit()
    return {"status": "ok", "message": "Expense added successfully"}


@app.post("/expenses/query")
def query_expenses(data: ExpenseCreate):
    query = "SELECT * FROM expenses WHERE date >= %s AND date <= %s"
    params = [data.start_date, data.end_date]

    if data.category:
        query += " AND category = %s"
        params.append(data.category)

    cur.execute(query, tuple(params))
    return {"expenses": cur.fetchall()}
