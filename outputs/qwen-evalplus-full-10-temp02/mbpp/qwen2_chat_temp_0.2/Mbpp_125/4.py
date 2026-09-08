def find_length(binary_string):
    """
    Finds the maximum difference between the number of 0s and number of 1s in any sub-string of the given binary string.
    
    Args:
    binary_string (str): A binary string.
    
    Returns:
    int: The maximum difference found.
    """
    max_diff = 0
    current_diff = 0
    for char in binary_string:
        if char == '0':
            current_diff += 1
        else:
            current_diff -= 1
        max_diff = max(max_diff, current_diff)
    return max_diff
