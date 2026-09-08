def neg_nos(lst):
    """
    This function takes a list of numbers as input and returns a new list containing only the negative numbers from the original list.
    
    Args:
    lst (list): A list of numbers.
    
    Returns:
    list: A list containing only the negative numbers from the original list.
    """
    # Using list comprehension to filter out negative numbers
    return [num for num in lst if num < 0]
