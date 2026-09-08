def Split(numbers):
    """
    This function takes a list of numbers as input and returns a new list containing only the even numbers from the input list.
    
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
            # If it is even, append it to the even_numbers list
            even_numbers.append(number)
    # Return the list of even numbers
    return even_numbers