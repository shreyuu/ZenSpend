from langchain_ollama import OllamaLLM
from langchain.prompts import ChatPromptTemplate
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.memory import ConversationBufferMemory
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from .memory import save_conversation, query_memory
import re
import json
from typing import Dict, Any
from pydantic import BaseModel, Field
from datetime import date

# Set up the local LLM
llm = OllamaLLM(model="phi3:mini")  # Use a smaller model for testing


# Define tool schemas
class ExpenseCreateInput(BaseModel):
    amount: float = Field(..., description="Amount spent")
    category: str = Field(
        ..., description="Category of expense (e.g., Food, Transport)"
    )
    date: str = Field(
        default=str(date.today()), description="Date of expense in YYYY-MM-DD format"
    )
    description: str = Field(
        default=None, description="Optional description of expense"
    )


class ExpenseQueryInput(BaseModel):
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    category: str = Field(default=None, description="Optional category to filter by")


# Tool functions
def add_expense(input_json: str) -> str:
    """Add a new expense to the database."""
    try:
        # Parse the input to validate
        data = ExpenseCreateInput.parse_raw(input_json)

        # Here you would call your database function
        # For now, just return a confirmation
        return f"Successfully added expense: {data.amount} on {data.category} ({data.description}) on {data.date}"
    except Exception as e:
        return f"Error adding expense: {str(e)}"


def query_expenses(input_json: str) -> str:
    """Query expenses from the database."""
    try:
        # Parse the input to validate
        data = ExpenseQueryInput.parse_raw(input_json)

        # Here you would query your database
        # For now, just return a confirmation
        return f"Querying expenses from {data.start_date} to {data.end_date} in category {data.category or 'all'}"
    except Exception as e:
        return f"Error querying expenses: {str(e)}"


# Define tools
tools = [
    Tool.from_function(
        func=add_expense,
        name="add_expense",
        description="Add a new expense to the database",
        args_schema=ExpenseCreateInput,
    ),
    Tool.from_function(
        func=query_expenses,
        name="query_expenses",
        description="Query expenses from the database",
        args_schema=ExpenseQueryInput,
    ),
]

# Set up agent
system_message = """You are a helpful expense tracking assistant. 
You help users add expenses to their tracker and query information about their spending.
When a user mentions spending money, help them add it as an expense.
When they ask about their spending, help them query their expenses."""

prompt = ChatPromptTemplate.from_messages(
    [("system", system_message), ("human", "{input}"), ("ai", "{agent_scratchpad}")]
)

agent = (
    {
        "input": lambda x: x["input"],
        "agent_scratchpad": lambda x: format_to_openai_function_messages(
            x["intermediate_steps"]
        ),
    }
    | prompt
    | llm
    | OpenAIFunctionsAgentOutputParser()
)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


def get_llm_response(user_input: str) -> str:
    """Process user input through the agent."""
    try:
        # Get relevant context from memory
        memory_docs = query_memory(user_input)
        context = "\n".join(doc.page_content for doc in memory_docs)

        # Enhance the user input with context if available
        enhanced_input = user_input
        if context:
            enhanced_input = f"Context from previous conversations:\n{context}\n\nUser input: {user_input}"

        # Execute the agent
        response = agent_executor.invoke({"input": enhanced_input})
        output = response["output"]

        # Save conversation
        save_conversation(user_input, output)

        return output
    except Exception as e:
        print(f"Error processing request: {e}")
        return f"I'm sorry, I encountered an error: {str(e)}"


def extract_expense(user_input: str) -> Dict[str, Any]:
    """Extract expense details from natural language."""
    try:
        # Use the agent to process the input
        response = agent_executor.invoke(
            {"input": f"Extract expense details from this text: {user_input}"}
        )

        # Try to extract structured data from the response
        # This is a simplified approach - in practice you'd want to use the tool outputs
        match = re.search(r"\{.*\}", response["output"], re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass

        # Fallback: Basic regex extraction
        amount_match = re.search(r"(\d+)", user_input)
        if amount_match:
            amount = float(amount_match.group(1))

            # Very basic category detection
            category = "Miscellaneous"
            for keyword, cat in [
                (["food", "lunch", "dinner", "breakfast"], "Food"),
                (["transport", "uber", "ola", "taxi", "bus"], "Transport"),
                (["movie", "entertainment", "show"], "Entertainment"),
            ]:
                if any(k in user_input.lower() for k in keyword):
                    category = cat
                    break

            return {"amount": amount, "category": category, "note": user_input}
    except Exception as e:
        print(f"Error extracting expense: {e}")

    return None
