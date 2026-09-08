def is_samepatterns(patterns, patterns2):
    """
    Check if the given patterns array follows the sequence given in the patterns2 array.
    
    :param patterns: List of strings representing the patterns.
    :param patterns2: List of strings representing the patterns to compare against.
    :return: True if the patterns follow the sequence, False otherwise.
    """
    # Check if the lengths of the two lists are equal
    if len(patterns) != len(patterns2):
        return False
    
    # Iterate through the patterns and compare each with the corresponding pattern in patterns2
    for i in range(len(patterns)):
        if patterns[i] != patterns2[i]:
            return False
    
    # If all patterns match, return True
    return True