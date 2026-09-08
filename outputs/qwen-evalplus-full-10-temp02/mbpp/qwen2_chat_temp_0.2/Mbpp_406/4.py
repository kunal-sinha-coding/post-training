def find_Parity(number):
    """
    Determine if the parity of a given number is odd.
    
    Args:
    number (int): The number to check.
    
    Returns:
    bool: True if the parity of the number is odd, False otherwise.
    """
    # Check if the number is odd
    if number % 2 != 0:
        return True
    else:
        return False