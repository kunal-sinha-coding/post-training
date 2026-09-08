def multiple_to_single(numbers):
    """
    Join a list of multiple integers into a single integer.
    
    Args:
    numbers (list): A list of integers.
    
    Returns:
    int: The single integer formed by joining the integers in the list.
    """
    # Convert the list of integers to a single string
    num_str = ''.join(map(str, numbers))
    # Convert the string back to an integer
    result = int(num_str)
    return result