from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import re
import json

# Set up the local LLM (llama3, deepseek, etc.)
llm = Ollama(model="llama3.1:8b")

# Prompt Template
prompt = PromptTemplate.from_template(
    """Extract the amount, category, and note from this user input: {input}. 
    
For food items, use 'Food' as the category.
For beverages, use 'Drinks' as the category.
If multiple items are mentioned, sum up the total amount.

Respond in JSON format like {{"amount": 70, "category": "Food", "note": "Pani puri and coke"}}
"""
)

# Chain setup
chain = LLMChain(llm=llm, prompt=prompt)


def extract_expense(user_input: str):
    # First try using LLM
    try:
        result = chain.invoke({"input": user_input})
        parsed = extract_json_from_text(result["text"])
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
