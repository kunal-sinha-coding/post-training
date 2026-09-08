def noprofit_noloss(amount, profit):
    """
    Check if the given amount has no profit and no loss

    Args:
    amount (int): The total amount
    profit (int): The profit

    Returns:
    bool: True if the amount has no profit and no loss, False otherwise
    """
    # Check if the amount is greater than or equal to the profit
    if amount >= profit:
        return False
    # Check if the amount is less than the profit
    elif amount < profit:
        return True
    else:
        return False