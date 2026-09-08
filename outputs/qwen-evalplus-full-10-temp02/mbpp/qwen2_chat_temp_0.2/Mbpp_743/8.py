def rotate_right(lst, n):
    """
    Rotate a given list by specified number of items to the right direction.
    
    Parameters:
    lst (list): The list to be rotated.
    n (int): The number of items to rotate to the right.
    
    Returns:
    list: The rotated list.
    """
    # Check if the list is empty or has only one element
    if len(lst) <= 1:
        return lst
    
    # Calculate the effective rotation needed
    effective_rotation = n % len(lst)
    
    # Perform the rotation
    return lst[-effective_rotation:] + lst[:-effective_rotation]