def remove_lowercase(s):
    """
    Remove lowercase substrings from a given string.
    
    Args:
    s (str): The input string from which lowercase substrings will be removed.
    
    Returns:
    str: A new string with all lowercase substrings removed.
    """
    # Using list comprehension to filter out lowercase substrings
    return ''.join([char for char in s if char.isupper()])
