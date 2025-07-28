from .database import SessionLocal
from .models import Expense
from .utils import stringify_expense
from langchain.vectorstores.pgvector import PGVector
from langchain.embeddings import OllamaEmbeddings
from langchain.docstore.document import Document
import os
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("DATABASE_URL")
embedding = OllamaEmbeddings(model="llama3")

vectorstore = PGVector(
    connection_string=CONNECTION_STRING,
    collection_name="expense_embeddings",
    embedding_function=embedding,
)


def embed_expenses():
    session = SessionLocal()
    expenses = session.query(Expense).all()
    docs = [
        Document(page_content=stringify_expense(exp), metadata={"id": exp.id})
        for exp in expenses
    ]
    vectorstore.add_documents(docs)
    print(f"✅ Embedded {len(docs)} expenses.")


if __name__ == "__main__":
    embed_expenses()
