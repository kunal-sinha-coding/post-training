def find_Parity(number):
    """
    Determine if the parity (odd or even) of a given number is odd.
    
    Args:
    number (int): The number to check.
    
    Returns:
    bool: True if the parity is odd, False otherwise.
    """
    # Check if the number is even
    if number % 2 == 0:
        return False
    else:
        return True