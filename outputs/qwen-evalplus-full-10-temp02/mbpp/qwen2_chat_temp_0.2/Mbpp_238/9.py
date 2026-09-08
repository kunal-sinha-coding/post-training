def number_of_substrings(s):
    """
    Count the number of non-empty substrings of a given string.
    
    Args:
    s (str): The input string.
    
    Returns:
    int: The count of non-empty substrings.
    """
    count = 0
    for i in range(len(s)):
        for j in range(i + 1, len(s) + 1):
            count += 1
    return count
