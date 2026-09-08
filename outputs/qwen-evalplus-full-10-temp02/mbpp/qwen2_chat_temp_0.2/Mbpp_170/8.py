def sum_range_list(numbers, start, end):
    """
    Calculate the sum of numbers in a list within a specified range.
    
    Parameters:
    numbers (list): The list of numbers to sum.
    start (int): The starting index of the range.
    end (int): The ending index of the range.
    
    Returns:
    int: The sum of numbers within the specified range.
    """
    # Ensure the start index is less than or equal to the end index
    if start > end:
        start, end = end, start
    
    # Calculate the sum of the specified range
    total_sum = sum(numbers[start:end+1])
    
    return total_sum
