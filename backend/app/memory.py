from xml.dom.minidom import Document
from langchain_community.vectorstores import PGVector
from langchain_community.embeddings import OllamaEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain_ollama import ChatOllama
from langchain.chains import ConversationChain
import os

# Load environment
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("DATABASE_URL")

# Create embedding + vector store
# embedding = OllamaEmbeddings(model="llama3.1:8b")
embedding = OllamaEmbeddings(model="phi3:mini")  # Use a smaller model for testing
vectorstore = PGVector(
    connection_string=CONNECTION_STRING,
    collection_name="memory_store",
    embedding_function=embedding,
)


def save_conversation(user_msg: str, ai_msg: str):
    docs = [
        Document(page_content=user_msg, metadata={"role": "user"}),
        Document(page_content=ai_msg, metadata={"role": "ai"}),
    ]
    vectorstore.add_documents(docs)


def query_memory(query: str):
    return vectorstore.similarity_search(query, k=3)


# Conversation memory chain
# llm = ChatOllama(model="llama3.1:8b")
llm = ChatOllama(model="phi3:mini")  # Use a smaller model for testing
memory = ConversationBufferMemory(memory_key="history", return_messages=True)

conversation_chain = ConversationChain(llm=llm, verbose=True, memory=memory)
