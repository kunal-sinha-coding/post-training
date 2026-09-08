def noprofit_noloss(amount, cost):
    """
    Check if the given amount has no profit and no loss.
    
    Args:
    amount (int): The total amount to be spent.
    cost (int): The total cost to be paid.
    
    Returns:
    bool: True if the amount has no profit and no loss, False otherwise.
    """
    # Calculate the profit if the amount is greater than the cost
    profit = amount - cost
    
    # Check if the profit is zero
    if profit == 0:
        return True
    
    # Check if the profit is negative
    if profit < 0:
        return False
    
    # If the profit is positive, it means there is no loss
    return True