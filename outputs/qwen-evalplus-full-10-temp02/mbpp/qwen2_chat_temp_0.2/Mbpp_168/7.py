def frequency(lst, num):
    """
    Count the number of occurrences of a number in a given list.
    
    Parameters:
    lst (list): The list in which to count occurrences of the number.
    num (int): The number to count in the list.
    
    Returns:
    int: The number of occurrences of the number in the list.
    """
    count = 0
    for item in lst:
        if item == num:
            count += 1
    return count