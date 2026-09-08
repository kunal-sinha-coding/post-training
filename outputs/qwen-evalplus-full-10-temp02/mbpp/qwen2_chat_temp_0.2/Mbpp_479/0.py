def first_Digit(number):
    """
    This function takes an integer as input and returns its first digit.
    
    Parameters:
    number (int): The integer whose first digit is to be found.
    
    Returns:
    int: The first digit of the given number.
    """
    # Check if the number is negative
    if number < 0:
        number = -number  # Make the number positive to find the first digit
    
    # Extract the first digit by taking the absolute value of the number
    first_digit = abs(number) % 10
    
    return first_digit