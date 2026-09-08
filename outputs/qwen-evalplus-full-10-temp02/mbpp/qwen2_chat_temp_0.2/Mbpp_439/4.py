def multiple_to_single(numbers):
    """
    Join a list of multiple integers into a single integer.
    
    Args:
    numbers (list): A list of integers.
    
    Returns:
    int: The joined integer.
    """
    # Convert the list of integers into a single string
    num_str = ''.join(map(str, numbers))
    # Convert the string back to an integer
    result = int(num_str)
    return result