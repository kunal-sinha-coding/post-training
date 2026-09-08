def move_zeroes(lst):
    """
    Move all zeroes to the end of the given list.
    
    Args:
    lst (list): The input list containing elements.
    
    Returns:
    list: The list with zeroes moved to the end.
    """
    # Initialize pointers for the start and end of the list
    start = 0
    end = len(lst) - 1
    
    # Traverse the list
    while start <= end:
        # If the current element is not zero, move it to the start
        if lst[start] != 0:
            lst[start], lst[end] = lst[end], lst[start]
            start += 1
        # Move the end pointer to the right if the current element is zero
        end -= 1
    
    return lst