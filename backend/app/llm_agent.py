from multiprocessing import context
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from .memory import conversation_chain, save_conversation, query_memory
from langchain_core.prompts import ChatPromptTemplate
import re
import json

# Set up the local LLM (llama3, deepseek, etc.)
llm = OllamaLLM(model="llama3.1:8b")

# Prompt Template
prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful expense assistant. Here is the past context:\n{context}",
        ),
        ("human", "{input}"),
    ]
)


# Chain setup using the newer runnable syntax
chain = prompt_template | llm


def get_llm_response(user_input: str):
    memory_docs = query_memory(user_input)
    context = "\n".join(doc.page_content for doc in memory_docs)

    response = chain.invoke({"input": user_input, "context": context})

    save_conversation(user_input, response)
    return response


def extract_expense(user_input: str):
    # First try using LLM
    try:
        result = chain.invoke({"input": user_input})
        parsed = extract_json_from_text(result)
        if parsed and "amount" in parsed and "category" in parsed:
            return parsed
    except Exception as e:
        print(f"LLM extraction error: {e}")

    # Fallback: Basic regex pattern matching for common Indian expense formats
    try:
        # Look for amounts with ₹ symbol
        amounts = re.findall(r"₹(\d+)", user_input)
        if amounts:
            total_amount = sum(int(amount) for amount in amounts)

            # Basic category detection
            category = "Food"  # Default
            if any(
                food in user_input.lower()
                for food in ["pani puri", "food", "lunch", "dinner", "breakfast"]
            ):
                category = "Food"
            elif any(
                drink in user_input.lower()
                for drink in ["coke", "pepsi", "soda", "drink", "tea", "coffee"]
            ):
                category = "Drinks"

            return {
                "amount": float(total_amount),
                "category": category,
                "note": user_input,
            }
    except Exception as e:
        print(f"Fallback extraction error: {e}")

    return None


def extract_json_from_text(text):
    """Helper to extract JSON from text that might have other content."""
    try:
        # Try to find JSON-like content in the text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)

        # If no JSON pattern found, try evaluating the whole text
        return eval(text)
    except Exception:
        return None


def chat_with_memory(user_input: str) -> str:
    """Function to chat with memory using the conversation chain."""
    response = conversation_chain.predict(input=user_input)
    return response
