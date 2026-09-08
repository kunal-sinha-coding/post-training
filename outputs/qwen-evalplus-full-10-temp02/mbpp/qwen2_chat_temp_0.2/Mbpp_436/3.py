def neg_nos(lst):
    """
    This function takes a list of integers and returns a new list containing only the negative numbers from the original list.
    
    Parameters:
    lst (list): A list of integers.
    
    Returns:
    list: A list containing only the negative numbers from the original list.
    """
    # Using list comprehension to filter out negative numbers
    return [num for num in lst if num < 0]
