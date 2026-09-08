def find_length(binary_string):
    """
    This function takes a binary string as input and returns the maximum difference between the number of 0s and 1s in any sub-string of the given binary string.
    
    Args:
    binary_string (str): A binary string.
    
    Returns:
    int: The maximum difference between the number of 0s and 1s in any sub-string.
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
