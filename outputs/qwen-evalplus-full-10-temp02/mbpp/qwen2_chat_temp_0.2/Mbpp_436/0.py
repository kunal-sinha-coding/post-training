def neg_nos(lst):
    """
    Return the negative numbers in a list.
    
    Args:
    lst (list): A list of integers.
    
    Returns:
    list: A list containing only the negative numbers from the input list.
    """
    # Use list comprehension to filter out negative numbers
    return [num for num in lst if num < 0]