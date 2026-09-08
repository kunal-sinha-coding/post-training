def is_samepatterns(patterns, patterns2):
    """
    Check if the given patterns array follows the sequence given in the patterns2 array.
    
    Parameters:
    patterns (list of str): The first list of patterns.
    patterns2 (list of str): The second list of patterns.
    
    Returns:
    bool: True if the patterns follow the sequence, False otherwise.
    """
    # Check if the length of patterns is equal to the length of patterns2
    if len(patterns) != len(patterns2):
        return False
    
    # Iterate through the patterns and check if each pattern matches the corresponding pattern in patterns2
    for i in range(len(patterns)):
        if patterns[i] != patterns2[i]:
            return False
    
    # If all patterns match, return True
    return True