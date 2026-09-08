def Split(numbers):
    """
    This function takes a list of numbers and returns a new list containing only the even numbers.
    
    Args:
    numbers (list): A list of integers.
    
    Returns:
    list: A list containing only the even numbers from the input list.
    """
    # Initialize an empty list to store even numbers
    even_numbers = []
    
    # Iterate through each number in the input list
    for number in numbers:
        # Check if the number is even
        if number % 2 == 0:
            # Append the even number to the even_numbers list
            even_numbers.append(number)
    
    # Return the list of even numbers
    return even_numbers