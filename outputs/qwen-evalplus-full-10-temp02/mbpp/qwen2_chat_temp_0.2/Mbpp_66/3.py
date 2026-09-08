def pos_count(numbers):
    """
    Count the number of positive numbers in a list.
    
    Args:
    numbers (list): A list of integers.
    
    Returns:
    int: The count of positive numbers in the list.
    """
    count = 0
    for num in numbers:
        if num > 0:
            count += 1
    return count