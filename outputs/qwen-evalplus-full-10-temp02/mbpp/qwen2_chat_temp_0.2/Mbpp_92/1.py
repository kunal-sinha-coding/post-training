def is_undulating(number):
    """
    Check if the given number is undulating.
    
    An undulating number is a number where the difference between consecutive digits is not constant.
    
    Parameters:
    number (int): The number to check.
    
    Returns:
    bool: True if the number is undulating, False otherwise.
    """
    # Convert the number to a string to iterate over each digit
    number_str = str(number)
    # Initialize the difference between consecutive digits
    difference = 0
    
    # Iterate over the string representation of the number
    for i in range(1, len(number_str)):
        # Calculate the difference between consecutive digits
        difference = abs(int(number_str[i]) - int(number_str[i-1]))
        # Check if the difference is not constant
        if difference != 0:
            return False
    
    # If all differences are constant, the number is undulating
    return True