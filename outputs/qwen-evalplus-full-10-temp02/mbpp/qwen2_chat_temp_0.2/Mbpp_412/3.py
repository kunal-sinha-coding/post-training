def remove_odd(numbers):
    """
    Remove odd numbers from a given list.
    
    Args:
    numbers (list): A list of integers.
    
    Returns:
    list: A list with all odd numbers removed.
    """
    # Using list comprehension to filter out odd numbers
    return [num for num in numbers if num % 2 == 0]
