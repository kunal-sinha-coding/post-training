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
    
    # Move the elements to the end of the list
    while left <= right:
        if lst[left] == 0:
            # Move the element to the end
            lst[right], lst[left] = lst[left], lst[right]
            right -= 1
        else:
            # Move the pointer to the right
            left += 1
    
    return lst