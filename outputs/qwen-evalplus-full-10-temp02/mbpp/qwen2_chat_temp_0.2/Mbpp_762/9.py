def check_monthnumber_number(month_number):
    """
    Check whether the given month number contains 30 days or not. Months are given as number from 1 to 12.
    
    Args:
    month_number (int): The month number to check.
    
    Returns:
    bool: True if the month number contains 30 days, False otherwise.
    """
    # Check if the month number is between 1 and 12
    if 1 <= month_number <= 12:
        # Check if the month number is 6 or 9
        if month_number == 6 or month_number == 9:
            return True
    return False