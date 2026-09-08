def check_monthnumb_number(month):
    """
    Check whether the given month number contains 31 days or not.
    
    Args:
    month (int): The month number to check.
    
    Returns:
    bool: True if the month contains 31 days, False otherwise.
    """
    # List of months with 31 days
    months_with_31_days = [1, 3, 5, 7, 8, 10, 12]
    
    # Check if the month is in the list of months with 31 days
    return month in months_with_31_days