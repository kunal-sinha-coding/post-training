def is_undulating(number):
    """
    Check if the given number is undulating or not.
    
    Args:
    number (int): The number to check.
    
    Returns:
    bool: True if the number is undulating, False otherwise.
    """
    # Convert the number to a string to easily iterate over each digit
    num_str = str(number)
    # Check if the number is a palindrome
    if num_str == num_str[::-1]:
        # Check if the number has an odd number of digits
        if len(num_str) % 2 != 0:
            return True
    return False