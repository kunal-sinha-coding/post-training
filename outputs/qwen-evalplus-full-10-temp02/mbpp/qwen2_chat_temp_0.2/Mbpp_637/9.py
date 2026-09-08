def noprofit_noloss(amount, profit):
    """
    Check if the given amount has no profit and no loss
    :param amount: The total amount
    :param profit: The profit amount
    :return: True if no profit and no loss, False otherwise
    """
    # Check if the profit is greater than the amount
    if profit > amount:
        return False
    # Check if the profit is less than or equal to the amount
    if profit <= amount:
        return True
    # If neither condition is met, return False
    return False