def remove_odd(numbers):
    """
    This function takes a list of numbers and returns a new list with all odd numbers removed.
    
    Args:
    numbers (list): A list of integers.
    
    Returns:
    list: A new list with all odd numbers removed.
    """
    # Using list comprehension to filter out odd numbers
    return [num for num in numbers if num % 2 == 0]
