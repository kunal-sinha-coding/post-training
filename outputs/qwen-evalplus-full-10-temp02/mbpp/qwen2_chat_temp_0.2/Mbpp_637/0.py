def noprofit_noloss(amount, cost):
    """
    Check if the given amount has no profit and no loss.
    
    Args:
    amount (int): The total amount to be spent.
    cost (int): The total cost of the items.
    
    Returns:
    bool: True if the amount has no profit and no loss, False otherwise.
    """
    # Calculate the profit if the amount is greater than the cost
    profit = amount - cost
    # Check if the profit is zero or negative
    if profit == 0 or profit < 0:
        return False
    else:
        return True