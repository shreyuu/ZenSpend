from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain.schema import HumanMessage, AIMessage
from langchain.agents.format_scratchpad import format_log_to_messages
from langchain.agents.output_parsers import ReActSingleInputOutputParser
from langchain.output_parsers import OutputFixingParser
from langchain_core.output_parsers import PydanticOutputParser
from .memory import save_conversation, query_memory
from datetime import date, timedelta
import re
import json
from typing import Dict, Any
from pydantic import BaseModel, Field

# Define the input schema for creating an expense
FORMAT_INSTRUCTIONS = """
STRICTLY follow this format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

CRITICAL: You MUST include "Action:" immediately after "Thought:" when using tools.
"""

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
    try:
        return json.loads(input_str)
    except Exception:
        pass

    kv = {}
    for part in re.split(r"[;,]\s*|\n", input_str):
        if "=" in part:
            k, v = part.split("=", 1)
            kv[k.strip().lower()] = v.strip()
    if kv:
        return kv

    out: Dict[str, Any] = {}

    amt = re.search(r"(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)", input_str, flags=re.IGNORECASE)
    if amt:
        out["amount"] = float(amt.group(1))

    lower = input_str.lower()
    if any(w in lower for w in ["grocery", "groceries", "supermarket"]):
        out["category"] = "Groceries"
    elif any(w in lower for w in ["food", "lunch", "dinner", "breakfast"]):
        out["category"] = "Food"
    elif any(w in lower for w in ["transport", "uber", "ola", "taxi", "bus"]):
        out["category"] = "Transport"

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
    try:
        raw = _parse_flexible_input(input_json)
        if "date" not in raw or not raw["date"]:
            raw["date"] = str(date.today())
        if "description" not in raw:
            raw["description"] = None
        data = ExpenseCreateInput(**raw)
        return f"Successfully added expense: {data.amount} on {data.category} ({data.description}) on {data.date}"
    except Exception as e:
        return f"Error adding expense: {str(e)}"


def query_expenses(input_json: str) -> str:
    try:
        raw = _parse_flexible_input(input_json)
        data = ExpenseQueryInput(**raw)
        return f"Querying expenses from {data.start_date} to {data.end_date} in category {data.category or 'all'}"
    except Exception as e:
        return f"Error querying expenses: {str(e)}"


def add_expense_tool(amount: int, category: str, date: str):
    """Add an expense to the system"""
    try:
        # Your expense addition logic here
        expense_data = {"amount": amount, "category": category, "date": date}
        # Add to database/storage
        return f"Successfully added expense: ₹{amount} for {category} on {date}"
    except Exception as e:
        return f"Error adding expense: {str(e)}"


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
    Tool(
        name="add_expense_tool",
        func=add_expense_tool,
        description="Add an expense. Input should be: amount (number), category (string), date (YYYY-MM-DD format)",
    ),
]

# Create ReAct agent prompt with required variables
tool_names = [tool.name for tool in tools]
tool_descriptions = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])

# Use the FORMAT_INSTRUCTIONS in the prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a helpful expense tracking assistant.
You help users add expenses to their tracker and query information about their spending.
When a user mentions spending money, help them add it as an expense.
When they ask about their spending, help them query their expenses.
If the user provides a date like 'July 27', assume the year is the current year unless specified, and format as YYYY-MM-DD.

You can use the following tools:

{tools}

{format_instructions}
""",
        ),
        ("human", "{input}"),
        ("ai", "{agent_scratchpad}"),
    ]
)

# Partial-fill the required fields
prompt = prompt.partial(
    tool_names=", ".join(tool_names),
    tools=tool_descriptions,
    format_instructions=FORMAT_INSTRUCTIONS.format(tool_names=", ".join(tool_names)),
)

# Create the ReAct agent and executor with proper scratchpad handling
agent = create_react_agent(
    llm, tools, prompt, output_parser=ReActSingleInputOutputParser()
)
agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=10,
    max_execution_time=60,
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

        # Execute the agent with proper input format
        response = agent_executor.invoke({"input": enhanced_input})
        output = response["output"]

        # Save conversation
        save_conversation(user_input, output)

        return output
    except Exception as e:
        print(f"Error processing request: {e}")
        return f"I'm sorry, I encountered an error: {str(e)}"


# Create a Pydantic parser for expense data
expense_parser = PydanticOutputParser(pydantic_object=ExpenseCreateInput)

# Wrap with fixing capability for more robust parsing
fixing_parser = OutputFixingParser.from_llm(parser=expense_parser, llm=llm)


def extract_expense(user_input: str) -> Dict[str, Any]:
    try:
        # Remove agent_scratchpad from input - let the agent handle it internally
        response = agent_executor.invoke(
            {"input": f"Extract expense details from this text: {user_input}"}
        )
        match = re.search(r"\{.*\}", response["output"], re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                # Try to fix the output with our fixing parser
                try:
                    return fixing_parser.parse(response["output"])
                except:
                    pass

        # Extract amount
        amount_match = re.search(r"(\d+)", user_input)
        if amount_match:
            amount = float(amount_match.group(1))

            # Extract category
            category = "Miscellaneous"
            category_map = {
                "food": ["food", "lunch", "dinner", "breakfast", "restaurant", "meal"],
                "transport": ["transport", "uber", "ola", "taxi", "bus", "travel"],
                "entertainment": ["movie", "entertainment", "show", "concert"],
                "shopping": ["shopping", "clothes", "dress", "shirt"],
                "books": ["book", "books", "novel", "textbook"],
                "groceries": ["groceries", "grocery", "supermarket"],
            }

            for cat, keywords in category_map.items():
                if any(keyword in user_input.lower() for keyword in keywords):
                    category = cat.capitalize()
                    break

            # Extract date with relative references
            expense_date = date.today()  # Default to today

            # Handle relative date references
            if "yesterday" in user_input.lower():
                expense_date = date.today() - timedelta(days=1)
            elif "last week" in user_input.lower():
                expense_date = date.today() - timedelta(days=7)
            elif "last month" in user_input.lower():
                # Approximate last month as 30 days ago
                expense_date = date.today() - timedelta(days=30)

            return {
                "amount": amount,
                "category": category,
                "description": user_input,
                "date": expense_date,
            }
    except Exception as e:
        print(f"Error extracting expense: {e}")
    return None
