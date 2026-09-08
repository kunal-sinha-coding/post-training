def sum_negativenum(numbers):
    """
    Calculate the sum of the negative numbers in a given list of numbers.
    
    Args:
    numbers (list): A list of integers.
    
    Returns:
    int: The sum of the negative numbers in the list.
    """
    # Initialize the sum to 0
    total_sum = 0
    
    # Iterate through each number in the list
    for num in numbers:
        # Check if the number is negative
        if num < 0:
            # Add the negative number to the total sum
            total_sum += num
    
    # Return the total sum of negative numbers
    return total_sum