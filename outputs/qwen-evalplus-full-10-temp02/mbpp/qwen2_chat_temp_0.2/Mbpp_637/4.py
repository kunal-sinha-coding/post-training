def noprofit_noloss(amount, cost):
    """
    Check if the given amount has no profit and no loss.
    
    Args:
    amount (int): The total amount of money.
    cost (int): The cost of the item.
    
    Returns:
    bool: True if the amount has no profit and no loss, False otherwise.
    """
    # Check if the amount is greater than the cost
    if amount > cost:
        return False
    # Check if the amount is less than the cost
    if amount < cost:
        return True
    # If the amount is equal to the cost, it's a loss
    if amount == cost:
        return False
    return True