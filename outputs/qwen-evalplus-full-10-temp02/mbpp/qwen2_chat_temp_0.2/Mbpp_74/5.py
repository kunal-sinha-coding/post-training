def is_samepatterns(patterns, patterns2):
    """
    Check if the given patterns array follows the sequence given in the patterns2 array.
    
    Parameters:
    patterns (list of str): The first list of patterns.
    patterns2 (list of str): The second list of patterns.
    
    Returns:
    bool: True if the patterns follow the sequence, False otherwise.
    """
    # Check if the length of patterns and patterns2 are the same
    if len(patterns) != len(patterns2):
        return False
    
    # Iterate through the patterns and patterns2 lists
    for i in range(len(patterns)):
        # Check if the current pattern in patterns matches the current pattern in patterns2
        if patterns[i] != patterns2[i]:
            return False
    
    # If all patterns match, return True
    return True