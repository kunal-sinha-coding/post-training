def find_Parity(number):
    """
    Determine if the parity of a given number is odd.
    
    Args:
    number (int): The number to check.
    
    Returns:
    bool: True if the number's parity is odd, False otherwise.
    """
    # Check if the number is odd by using the modulus operator
    if number % 2 != 0:
        return True
    else:
        return False