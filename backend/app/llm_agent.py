from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from .memory import save_conversation, query_memory
import re
import json
from datetime import date, datetime
from typing import Dict, Any
from pydantic import BaseModel, Field

# Set up the local LLM (chat model)
llm = ChatOllama(model="phi3:mini", temperature=0)


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


# Tool functions (accept flexible, non-JSON inputs too)
MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        start=1,
    )
}


def _parse_flexible_input(input_str: str) -> Dict[str, Any]:
    # Try JSON first
    try:
        return json.loads(input_str)
    except Exception:
        pass

    # key=value pairs
    kv = {}
    for part in re.split(r"[;,]\s*|\n", input_str):
        if "=" in part:
            k, v = part.split("=", 1)
            kv[k.strip().lower()] = v.strip()
    if kv:
        return kv

    # Fallback heuristics
    out: Dict[str, Any] = {}

    # amount (supports ₹ or Rs)
    amt = re.search(r"(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)", input_str, flags=re.IGNORECASE)
    if amt:
        out["amount"] = float(amt.group(1))

    # category (very simple)
    lower = input_str.lower()
    if any(w in lower for w in ["grocery", "groceries", "supermarket"]):
        out["category"] = "Groceries"
    elif any(w in lower for w in ["food", "lunch", "dinner", "breakfast"]):
        out["category"] = "Food"
    elif any(w in lower for w in ["transport", "uber", "ola", "taxi", "bus"]):
        out["category"] = "Transport"

    # date like "July 27" or "27 July"
    m1 = re.search(r"\b([A-Za-z]+)\s+(\d{1,2})\b", input_str)
    m2 = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\b", input_str)
    year = date.today().year
    if m1 and m1.group(1).lower() in MONTHS:
        mm = MONTHS[m1.group(1).lower()]
        dd = int(m1.group(2))
        out["date"] = f"{year:04d}-{mm:02d}-{dd:02d}"
    elif m2 and m2.group(2).lower() in MONTHS:
        mm = MONTHS[m2.group(2).lower()]
        dd = int(m2.group(1))
        out["date"] = f"{year:04d}-{mm:02d}-{dd:02d}"

    return out


def add_expense(input_json: str) -> str:
    """Add a new expense to the database."""
    try:
        # Parse input (JSON or free text)
        raw = _parse_flexible_input(input_json)

        # Defaults
        if "date" not in raw or not raw["date"]:
            raw["date"] = str(date.today())
        if "description" not in raw:
            raw["description"] = None

        # Validate via Pydantic
        data = ExpenseCreateInput(**raw)

        # Here you would call your database function
        return f"Successfully added expense: {data.amount} on {data.category} ({data.description}) on {data.date}"
    except Exception as e:
        return f"Error adding expense: {str(e)}"


def query_expenses(input_json: str) -> str:
    """Query expenses from the database."""
    try:
        raw = _parse_flexible_input(input_json)
        data = ExpenseQueryInput(**raw)

        # Here you would query your database
        return f"Querying expenses from {data.start_date} to {data.end_date} in category {data.category or 'all'}"
    except Exception as e:
        return f"Error querying expenses: {str(e)}"


# Define tools
tools = [
    Tool.from_function(
        func=add_expense,
        name="add_expense",
        description="Add a new expense to the database. Provide amount, category, date (YYYY-MM-DD), and optional description.",
        args_schema=ExpenseCreateInput,
    ),
    Tool.from_function(
        func=query_expenses,
        name="query_expenses",
        description="Query expenses from the database. Provide start_date, end_date (YYYY-MM-DD), and optional category.",
        args_schema=ExpenseQueryInput,
    ),
]

# Set up agent
system_message = """You are a helpful expense tracking assistant.
You help users add expenses to their tracker and query information about their spending.
When a user mentions spending money, help them add it as an expense.
When they ask about their spending, help them query their expenses.
If the user provides a date like 'July 27', assume the year is the current year unless specified, and format as YYYY-MM-DD.

IMPORTANT: When using tools, follow this exact format without any JSON code blocks or markdown formatting:
Action: <tool_name>
Action Input: <tool_input>
"""

# Get tool names and descriptions for the prompt
tool_names = [tool.name for tool in tools]
tool_descriptions = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])

# Create the prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_message + "\n\nAvailable tools:\n{tools}"),
        ("human", "{input}"),
        ("human", "{agent_scratchpad}"),
    ]
)

# Partial the prompt with tools info
prompt = prompt.partial(tools=tool_descriptions)

# Build the agent
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,  # Handle parsing errors
)


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

            return {"amount": amount, "category": category, "description": user_input}
    except Exception as e:
        print(f"Error extracting expense: {e}")

    return None
