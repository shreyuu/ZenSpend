from langchain_postgres import PGVector
from langchain_ollama import OllamaEmbeddings
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnablePassthrough, RunnableWithMessageHistory
from langchain_ollama import ChatOllama
from langchain.memory import ConversationSummaryMemory
from langchain.chains import ConversationChain
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
memory = ConversationSummaryMemory(llm=llm, memory_key="history")

# Setup message history
chat_history = InMemoryChatMessageHistory()


# Create a simple chain
def get_chat_chain():
    chain = (
        RunnablePassthrough.assign(chat_history=lambda x: x.get("chat_history", []))
        | llm
    )

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


from langchain_postgres.vectorstores import PGVector
import inspect

print(inspect.signature(PGVector.__init__))
