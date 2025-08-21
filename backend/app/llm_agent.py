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
import logging
import sys
from typing import Dict, Any
from pydantic import BaseModel, Field
from langchain.callbacks.base import BaseCallbackHandler

# Set up logging for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("agent_debug.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("llm_agent")

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
logger.info("Initialized Ollama LLM with model: phi3:mini")


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
    """Parse various input formats into a structured dictionary."""
    logger.debug(f"Parsing flexible input: {input_str}")
    try:
        return json.loads(input_str)
    except Exception as e:
        logger.debug(f"JSON parsing failed: {e}")
        pass

    kv = {}
    for part in re.split(r"[;,]\s*|\n", input_str):
        if "=" in part:
            k, v = part.split("=", 1)
            kv[k.strip().lower()] = v.strip()
    if kv:
        logger.debug(f"Key-value parsing successful: {kv}")
        return kv

    out: Dict[str, Any] = {}

    amt = re.search(r"(?:₹|rs\.?\s*)?(\d+(?:\.\d+)?)", input_str, flags=re.IGNORECASE)
    if amt:
        out["amount"] = float(amt.group(1))
        logger.debug(f"Extracted amount: {out['amount']}")

    lower = input_str.lower()
    if any(w in lower for w in ["grocery", "groceries", "supermarket"]):
        out["category"] = "Groceries"
    elif any(w in lower for w in ["food", "lunch", "dinner", "breakfast"]):
        out["category"] = "Food"
    elif any(w in lower for w in ["transport", "uber", "ola", "taxi", "bus"]):
        out["category"] = "Transport"

    if "category" in out:
        logger.debug(f"Extracted category: {out['category']}")

    m1 = re.search(r"\b([A-Za-z]+)\s+(\d{1,2})\b", input_str)
    m2 = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\b", input_str)
    year = date.today().year
    if m1 and m1.group(1).lower() in MONTHS:
        mm = MONTHS[m1.group(1).lower()]
        dd = int(m1.group(2))
        out["date"] = f"{year:04d}-{mm:02d}-{dd:02d}"
        logger.debug(f"Extracted date (pattern 1): {out['date']}")
    elif m2 and m2.group(2).lower() in MONTHS:
        mm = MONTHS[m2.group(2).lower()]
        dd = int(m2.group(1))
        out["date"] = f"{year:04d}-{mm:02d}-{dd:02d}"
        logger.debug(f"Extracted date (pattern 2): {out['date']}")

    logger.debug(f"Final flexible parsing result: {out}")
    return out


def add_expense(input_json: str) -> str:
    """Add an expense using the input JSON or flexible text."""
    logger.info(f"Adding expense with input: {input_json}")
    try:
        # Parse the input - this is the key fix
        if isinstance(input_json, str):
            try:
                # Try to parse as JSON first
                raw = json.loads(input_json)
                logger.debug(f"Successfully parsed JSON input: {raw}")
            except json.JSONDecodeError:
                # Fall back to flexible parsing if not valid JSON
                raw = _parse_flexible_input(input_json)
        else:
            raw = input_json

        if "date" not in raw or not raw["date"]:
            raw["date"] = str(date.today())
            logger.debug(f"Using default date: {raw['date']}")
        if "description" not in raw:
            raw["description"] = None

        logger.debug(f"Parsed expense data: {raw}")
        data = ExpenseCreateInput(**raw)
        result = f"Successfully added expense: {data.amount} on {data.category} ({data.description}) on {data.date}"
        logger.info(f"Expense added: {result}")
        return result
    except Exception as e:
        error_msg = f"Error adding expense: {str(e)}"
        logger.error(error_msg)
        return error_msg


def query_expenses(input_json: str) -> str:
    """Query expenses using the input parameters."""
    logger.info(f"Querying expenses with input: {input_json}")
    try:
        raw = _parse_flexible_input(input_json)
        logger.debug(f"Parsed query parameters: {raw}")
        data = ExpenseQueryInput(**raw)
        result = f"Querying expenses from {data.start_date} to {data.end_date} in category {data.category or 'all'}"
        logger.info(f"Query executed: {result}")
        return result
    except Exception as e:
        error_msg = f"Error querying expenses: {str(e)}"
        logger.error(error_msg)
        return error_msg


def add_expense_tool(amount: int, category: str, date: str):
    """Add an expense to the system with direct parameters."""
    logger.info(
        f"Using direct expense tool with amount={amount}, category={category}, date={date}"
    )
    try:
        # Your expense addition logic here
        expense_data = {"amount": amount, "category": category, "date": date}
        # Add to database/storage
        result = f"Successfully added expense: ₹{amount} for {category} on {date}"
        logger.info(f"Direct expense added: {result}")
        return result
    except Exception as e:
        error_msg = f"Error adding expense: {str(e)}"
        logger.error(error_msg)
        return error_msg


# Define tools with improved descriptions
tools = [
    Tool.from_function(
        func=add_expense,
        name="add_expense",
        description="""Add a new expense to the database. 
        Usage: Provide JSON with 'amount' (number), 'category' (string), 'date' (YYYY-MM-DD format), and optional 'description'.
        Example: {"amount": 500, "category": "Food", "date": "2023-07-15", "description": "Lunch"}""",
        args_schema=ExpenseCreateInput,
    ),
    Tool.from_function(
        func=query_expenses,
        name="query_expenses",
        description="""Query expenses from the database. 
        Usage: Provide JSON with 'start_date' (YYYY-MM-DD), 'end_date' (YYYY-MM-DD), and optional 'category'.
        Example: {"start_date": "2023-07-01", "end_date": "2023-07-31", "category": "Food"}""",
        args_schema=ExpenseQueryInput,
    ),
    Tool(
        name="add_expense_tool",
        func=add_expense_tool,
        description="""Add an expense with specific parameters.
        Parameters: 
        - amount: The amount spent (number)
        - category: Category of expense (string)
        - date: Date of expense in YYYY-MM-DD format (string)
        Example usage: add_expense_tool(500, "Food", "2023-07-15")""",
    ),
]

logger.info(f"Initialized {len(tools)} tools: {[tool.name for tool in tools]}")

# Create ReAct agent prompt with required variables and IMPROVED formatting
tool_names = [tool.name for tool in tools]
tool_descriptions = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])

# Enhanced prompt template with more explicit instructions and examples
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a helpful expense tracking assistant called ZenSpend.
You help users add expenses to their tracker and query information about their spending.
When a user mentions spending money, help them add it as an expense.
When they ask about their spending, help them query their expenses.

IMPORTANT FORMATTING INSTRUCTIONS:
{format_instructions}

AVAILABLE TOOLS:
{tools}

EXAMPLES:

Example 1: Adding an expense
User: "I spent 500 rupees on groceries yesterday"
Assistant's thought process (not visible to user):
Question: The user wants to add an expense for groceries.
Thought: I need to extract the amount, category, and date to add an expense.
Action: add_expense
Action Input: {{"amount": 500, "category": "Groceries", "date": "2023-07-14", "description": "groceries"}}
Observation: Successfully added expense: 500 on Groceries (groceries) on 2023-07-14
Thought: I now know the final answer
Final Answer: I've added your expense of ₹500 for groceries on yesterday's date. Is there anything else you'd like to track?

Example 2: Querying expenses
User: "Show me my food expenses for July"
Assistant's thought process (not visible to user):
Question: The user wants to see their food expenses for July.
Thought: I need to query expenses with the appropriate date range and category filter.
Action: query_expenses
Action Input: {{"start_date": "2023-07-01", "end_date": "2023-07-31", "category": "Food"}}
Observation: Querying expenses from 2023-07-01 to 2023-07-31 in category Food
Thought: I now know the final answer
Final Answer: Here are your food expenses for July. You spent a total of ₹2,500 on Food in July.

If the user provides a date like 'July 27', assume the current year and format as YYYY-MM-DD.
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

# Create the ReAct agent and executor with proper scratchpad handling and debugging
logger.info("Creating ReAct agent with structured prompt")


class DebugCallbackHandler(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs):
        logger.debug(f"LLM PROMPT:\n{prompts[0]}")

    def on_llm_end(self, response, **kwargs):
        logger.debug(f"LLM RESPONSE:\n{response.generations[0][0].text}")

    def on_tool_start(self, serialized, input_str, **kwargs):
        logger.debug(f"TOOL START: {serialized['name']} with input: {input_str}")

    def on_tool_end(self, output, **kwargs):
        logger.debug(f"TOOL OUTPUT: {output}")

    def on_chain_start(self, serialized, inputs, **kwargs):
        logger.debug(f"CHAIN START: {serialized['name']} with inputs: {inputs}")

    def on_chain_end(self, outputs, **kwargs):
        logger.debug(f"CHAIN END: {outputs}")

    def on_agent_action(self, action, **kwargs):
        logger.debug(f"AGENT ACTION: {action}")

    def on_agent_finish(self, finish, **kwargs):
        logger.debug(f"AGENT FINISH: {finish}")


debug_callbacks = [DebugCallbackHandler()]

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
    callbacks=debug_callbacks,
)


def get_llm_response(user_input: str) -> str:
    """Process user input through the agent with enhanced debugging."""
    logger.info(f"Processing user input: {user_input}")
    try:
        # Get relevant context from memory
        memory_docs = query_memory(user_input)
        context = "\n".join(doc.page_content for doc in memory_docs)
        logger.debug(
            f"Retrieved context: {context[:200]}..."
            if context
            else "No context retrieved"
        )

        # Enhance the user input with context if available
        enhanced_input = user_input
        if context:
            enhanced_input = f"Context from previous conversations:\n{context}\n\nUser input: {user_input}"
            logger.debug(f"Enhanced input with context")

        # Execute the agent with proper input format
        logger.debug(f"Executing agent with input: {enhanced_input}")
        response = agent_executor.invoke({"input": enhanced_input})
        output = response["output"]
        logger.info(f"Agent response: {output[:100]}...")

        # Save conversation
        save_conversation(user_input, output)
        logger.debug("Saved conversation to memory")

        return output
    except Exception as e:
        error_msg = f"Error processing request: {e}"
        logger.error(error_msg, exc_info=True)
        return f"I'm sorry, I encountered an error: {str(e)}"


# Create a Pydantic parser for expense data
expense_parser = PydanticOutputParser(pydantic_object=ExpenseCreateInput)

# Wrap with fixing capability for more robust parsing
fixing_parser = OutputFixingParser.from_llm(parser=expense_parser, llm=llm)
logger.info("Initialized output fixing parser for expense data")


def extract_expense(user_input: str) -> Dict[str, Any]:
    """Extract expense details from user input with enhanced debugging."""
    logger.info(f"Extracting expense from: {user_input}")

    try:
        # Try direct pattern matching first (more reliable than agent for simple patterns)
        amount_match = re.search(r"(\d+)", user_input)
        if amount_match:
            amount = float(amount_match.group(1))

            # Extract category - look for common expense categories or default to "Miscellaneous"
            category = "Miscellaneous"
            furniture_terms = ["table", "chair", "furniture", "desk", "sofa", "couch"]
            food_terms = ["food", "lunch", "dinner", "breakfast", "meal", "restaurant"]
            transport_terms = ["uber", "taxi", "bus", "train", "transport", "travel"]

            for term in furniture_terms:
                if term.lower() in user_input.lower():
                    category = "Furniture"
                    break

            for term in food_terms:
                if term.lower() in user_input.lower():
                    category = "Food"
                    break

            for term in transport_terms:
                if term.lower() in user_input.lower():
                    category = "Transport"
                    break

            # Extract date - try to find date patterns
            expense_date = date.today()  # Default to today

            # Look for date formats like "26 July 2025" or "July 26, 2025"
            date_patterns = [
                r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",  # 26 July 2025
                r"([A-Za-z]+)\s+(\d{1,2})(?:,|\s)+(\d{4})",  # July 26, 2025
                r"(\d{1,2})/(\d{1,2})/(\d{4})",  # MM/DD/YYYY or DD/MM/YYYY
                r"(\d{4})-(\d{1,2})-(\d{1,2})",  # YYYY-MM-DD
            ]

            for pattern in date_patterns:
                date_match = re.search(pattern, user_input)
                if date_match:
                    if pattern == r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})":
                        day, month_name, year = date_match.groups()
                        month = MONTHS.get(
                            month_name.lower(), 1
                        )  # Default to January if not found
                        expense_date = date(int(year), month, int(day))
                    elif pattern == r"([A-Za-z]+)\s+(\d{1,2})(?:,|\s)+(\d{4})":
                        month_name, day, year = date_match.groups()
                        month = MONTHS.get(month_name.lower(), 1)
                        expense_date = date(int(year), month, int(day))
                    # Add other pattern handling as needed
                    break

            result = {
                "amount": amount,
                "category": category,
                "description": f"Purchase of {category.lower()}",
                "date": str(expense_date),
            }

            logger.info(f"Direct extraction result: {result}")
            return result

        # Fall back to agent-based extraction if direct pattern matching fails
        # Your existing agent-based extraction code...

    except Exception as e:
        logger.error(f"Error extracting expense: {e}", exc_info=True)

    logger.error("Expense extraction failed completely")
    return None


# Debug utility to test agent behavior
def test_agent_with_simple_query(query="I spent 500 on food yesterday"):
    """Test function to verify agent behavior with a simple query."""
    logger.info(f"TESTING AGENT with query: {query}")
    try:
        response = get_llm_response(query)
        logger.info(f"TEST RESPONSE: {response}")
        return response
    except Exception as e:
        logger.error(f"TEST ERROR: {e}", exc_info=True)
        return f"Test failed with error: {str(e)}"
