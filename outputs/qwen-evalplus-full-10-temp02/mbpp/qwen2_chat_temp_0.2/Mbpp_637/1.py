def noprofit_noloss(amount, cost):
    """
    Check if the given amount has no profit and no loss.
    
    Args:
    amount (int): The total amount to be checked.
    cost (int): The cost of the item.
    
    Returns:
    bool: True if the amount has no profit and no loss, False otherwise.
    """
    # Calculate the profit if the amount is greater than the cost
    profit = amount - cost
    # Check if the profit is zero
    if profit == 0:
        return True
    # Check if the profit is negative
    elif profit < 0:
        return False
    else:
        return True