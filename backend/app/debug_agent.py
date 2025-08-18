import logging
from .llm_agent import test_agent_with_simple_query

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("agent_debug.log"), logging.StreamHandler()],
)
logger = logging.getLogger("debug_agent")


def run_debug_tests():
    """Run a series of test queries to debug agent behavior."""
    logger.info("Starting debug test suite")

    test_cases = [
        "I spent 500 on food yesterday",
        "Show me my expenses from last week",
        "Add 2000 rupees for rent payment",
        "How much did I spend on groceries this month?",
        "I paid 150 for coffee on Monday",
    ]

    for i, test in enumerate(test_cases):
        logger.info(f"Test case #{i+1}: {test}")
        response = test_agent_with_simple_query(test)
        logger.info(f"Response: {response}")
        logger.info("-" * 50)

    logger.info("Debug test suite completed")


if __name__ == "__main__":
    run_debug_tests()
