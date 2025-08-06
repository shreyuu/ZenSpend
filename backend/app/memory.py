from langchain_postgres import PGVector
from langchain_ollama import OllamaEmbeddings
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory
from langchain_ollama import ChatOllama
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain.docstore.document import Document
from langchain_core.chat_history import InMemoryChatMessageHistory
from sqlalchemy import create_engine

import os

# Load environment
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("DATABASE_URL")
engine = create_engine(CONNECTION_STRING)

# Create embedding + vector store
# embedding = OllamaEmbeddings(model="llama3.1:8b")
embedding = OllamaEmbeddings(model="phi3:mini")  # Use a smaller model for testing
vectorstore = PGVector(
    embedding,
    connection=engine,
    collection_name="memory_store",
    use_jsonb=True,
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
llm = ChatOllama(model="phi3:mini")  # Use a smaller model for testing

# Setup message history
chat_history = InMemoryChatMessageHistory()

# Create a modern LangChain prompt with history
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful AI assistant for tracking expenses."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ]
)


# Create a simple chain
def get_chat_chain():
    chain = prompt | llm | StrOutputParser()

    # Wrap with message history handler
    chain_with_history = RunnableWithMessageHistory(
        chain,
        lambda session_id: chat_history,  # Return the same history for all sessions
        input_messages_key="input",
        history_messages_key="chat_history",
    )

    return chain_with_history


# Replace the conversation_chain variable
conversation_chain = get_chat_chain()
