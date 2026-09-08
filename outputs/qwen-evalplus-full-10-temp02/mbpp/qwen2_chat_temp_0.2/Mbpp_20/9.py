def is_woodball(number):
    """
    Check if the given number is woodball or not.
    
    Args:
    number (int): The number to check.
    
    Returns:
    bool: True if the number is woodball, False otherwise.
    """
    # Woodball numbers are numbers that are divisible by 3 and 5.
    return number % 3 == 0 and number % 5 == 0
