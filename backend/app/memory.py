from langchain.vectorstores.pgvector import PGVector
from langchain.embeddings import OllamaEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOllama
from langchain.chains import ConversationChain
import os

# Load environment
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = os.getenv("DATABASE_URL")

# Create embedding + vector store
embedding = OllamaEmbeddings(model="llama3.1:8b")
vectorstore = PGVector(
    connection_string=CONNECTION_STRING,
    collection_name="zenspend_memory",
    embedding_function=embedding,
)

# Conversation memory chain
llm = ChatOllama(model="llama3.1:8b")
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

conversation_chain = ConversationChain(llm=llm, verbose=True, memory=memory)
