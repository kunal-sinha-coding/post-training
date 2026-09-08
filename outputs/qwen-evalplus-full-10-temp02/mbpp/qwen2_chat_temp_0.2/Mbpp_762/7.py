def check_monthnumber_number(month_number):
    """
    Check if the given month number contains 30 days or not.
    
    Args:
    month_number (int): The month number from 1 to 12.
    
    Returns:
    bool: True if the month number contains 30 days, False otherwise.
    """
    # List of months with 30 days
    months_with_30_days = [1, 3, 5, 7, 8, 10, 12]
    
    # Check if the month number is in the list of months with 30 days
    return month_number in months_with_30_days
