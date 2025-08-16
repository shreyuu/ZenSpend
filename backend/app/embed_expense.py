from .database import SessionLocal
from .models import Expense
from .utils import stringify_expense
from langchain_postgres import PGVector
from langchain_ollama import OllamaEmbeddings
from langchain.docstore.document import Document
import os
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("DATABASE_URL")
embedding = OllamaEmbeddings(model="phi3:mini")

# Let PGVector create tables with proper schema
vectorstore = PGVector(
    embeddings=embedding,
    connection=CONNECTION_STRING,
    collection_name="expense_embeddings",
    use_jsonb=True,
    pre_delete_collection=False,  # Don't delete existing data
)


def embed_expenses():
    session = SessionLocal()
    expenses = session.query(Expense).all()
    docs = [
        Document(page_content=stringify_expense(exp), metadata={"id": exp.id})
        for exp in expenses
    ]
    # Use add_documents without explicit IDs to avoid conflicts
    vectorstore.add_documents(docs)
    print(f"✅ Embedded {len(docs)} expenses.")


if __name__ == "__main__":
    embed_expenses()
