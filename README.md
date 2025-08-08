# 🧘 ZenSpend

> A privacy-first, AI-powered expense tracker built using **FastAPI**, **PostgreSQL**, **LangChain**, and **React** — powered locally by **Ollama**.

ZenSpend helps you log and manage expenses using natural language like  
_"I spent ₹200 on groceries and ₹50 on chai today"_ — and stores it in a structured, searchable, and visual format.

## ✨ Features

- 💬 **Natural Language Logging** (via LLM - Ollama)
- 📊 **Visual Expense Breakdown** (React + Tailwind UI)
- 🧠 **AI Memory & Context** (LangChain + pgvector)
- 🔒 **Privacy-First**: Runs entirely on your machine
- 🔌 **API-first** architecture (FastAPI)
- 📱 **PWA-ready** (can be installed on mobile)

## 📦 Project Structure

```plaintext
ZenSpend/
├── backend/ # FastAPI backend with LangChain + Ollama
│ └── app/
│ ├── main.py # App entrypoint
│ ├── routes.py # API routes (expense endpoints)
│ ├── database.py # SQLAlchemy DB connection
│ ├── models.py # SQLAlchemy ORM models
│ ├── schemas.py # Pydantic request/response models
│ └── llm_agent.py # LLM expense parser using LangChain + Ollama
│
├── frontend/ # React frontend with Vite + Tailwind
│ ├── src/
│ │ ├── components/ # ExpenseForm, ExpenseList
│ │ ├── App.jsx # Main layout
│ │ └── main.jsx # React entrypoint
│
├── docker-compose.yml # PostgreSQL + pgvector setup
├── ZenSpend PostgreSQL.session.sql # SQL reference file (optional)
├── LICENSE # License info
└── README.md # You’re reading it!
```

## 🧰 Tech Stack

### 🧠 AI Layer

| Purpose             | Technology                                |
| ------------------- | ----------------------------------------- |
| Local LLM Inference | [Ollama](https://ollama.com/)             |
| LLM Memory & Chain  | [LangChain](https://www.langchain.com/)   |
| LLM Model           | `llama3`, `deepseek`, or any Ollama model |

### 🧩 Backend

| Layer             | Technology |
| ----------------- | ---------- |
| Web Server        | FastAPI    |
| ORM               | SQLAlchemy |
| Schema Validation | Pydantic   |
| Database Driver   | psycopg2   |

### 🗃️ Database

| Layer                   | Technology |
| ----------------------- | ---------- |
| RDBMS                   | PostgreSQL |
| Vector Search Extension | pgvector   |

### 🌐 Frontend

| Layer            | Technology                  |
| ---------------- | --------------------------- |
| Framework        | React (via Vite)            |
| Styling          | Tailwind CSS                |
| State Management | useState (Zustand optional) |
| Charting (TBD)   | Recharts or Chart.js        |
| Form Handling    | Controlled inputs           |

## 🚀 Getting Started

### 🔧 Prerequisites

- Python 3.10+
- Node.js 18+
- Docker Desktop (for PostgreSQL)
- Ollama installed locally

## ⚙️ 1. Start PostgreSQL (with pgvector)

```bash
docker-compose up -d
```

Database credentials:
• DB Name: zenspend
• Username: zenspend
• Password: zenspend123

### 🧠 2. Start LLM with Ollama

```bash
ollama run llama3.1:8b
# or use a smaller model for testing
ollama run phi3:mini
```

### 🐍 3. Run Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # or manually install packages
uvicorn app.main:app --reload
```

### ⚛️ 4. Run Frontend

```bash
cd frontend
npm install
npm run dev
```

## 📈 Roadmap

    •	Expense logging API
    •	React form UI
    •	Natural language LLM parsing
    •	Vector memory (LangChain + pgvector)
    •	Interactive Chat Interface
    •	Budget goal setting
    •	Export data to CSV
    •	PWA install button

## 🧪 Sample Usage

POST /chat-expense

{
"text": "Spent 300 on books and 120 on snacks"
}

Returns:

{
"amount": 300,
"category": "books",
"description": "snacks",
...
}

## 🤝 Contributing

PRs welcome! To contribute:

```bash
git clone https://github.com/shreyuu/ZenSpend.git
cd ZenSpend
git checkout -b feature/your-feature-name
# Make changes
git add .
git commit -m "Add your feature"
git push origin feature/your-feature-name
```
