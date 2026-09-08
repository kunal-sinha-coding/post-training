def Split(numbers):
    """
    This function takes a list of integers and returns a new list containing only the odd numbers.
    
    Args:
    numbers (list): A list of integers.
    
    Returns:
    list: A list containing only the odd numbers from the input list.
    """
    # Initialize an empty list to store odd numbers
    odd_numbers = []
    # Iterate through each number in the input list
    for number in numbers:
        # Check if the number is odd
        if number % 2 != 0:
            # If it is odd, append it to the odd_numbers list
            odd_numbers.append(number)
    # Return the list of odd numbers
    return odd_numbers