def pos_count(numbers):
    """
    Count the number of positive numbers in a list.
    
    Args:
    numbers (list): A list of integers.
    
    Returns:
    int: The count of positive numbers in the list.
    """
    # Initialize a counter for positive numbers
    positive_count = 0
    # Iterate through each number in the list
    for num in numbers:
        # Check if the number is positive
        if num > 0:
            # Increment the counter if the number is positive
            positive_count += 1
    # Return the total count of positive numbers
    return positive_count