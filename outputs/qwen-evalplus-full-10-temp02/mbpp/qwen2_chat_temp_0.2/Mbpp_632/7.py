def move_zeroes(lst):
    """
    Move all zeroes to the end of the given list.
    
    Parameters:
    lst (list): The input list of integers.
    
    Returns:
    list: The list with zeroes moved to the end.
    """
    # Initialize pointers for the start and end of the list
    left = 0
    right = len(lst) - 1
    
    # Traverse the list
    while left <= right:
        # If the current element is not zero, move it to the left
        if lst[left] != 0:
            lst[left], lst[right] = lst[right], lst[left]
            left += 1
        # Move the right pointer to the right
        right -= 1
    
    return lst