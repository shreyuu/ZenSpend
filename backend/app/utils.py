def stringify_expense(expense):
    """
    Convert an expense object to a string representation.

    Args:
        expense (dict): A dictionary representing an expense with keys like 'amount', 'date', etc.

    Returns:
        str: A string representation of the expense.
    """
    return (
        f"Spent ₹{expense['amount']} on {expense['description']} "
        f"({expense['category']}) at {expense.get('location', 'unspecified location')} on {expense['date'].strftime('%Y-%m-%d')}"
    )
