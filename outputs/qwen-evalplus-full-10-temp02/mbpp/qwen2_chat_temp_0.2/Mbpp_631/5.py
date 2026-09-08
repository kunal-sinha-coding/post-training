def replace_spaces(s):
    """
    Replace whitespaces in the given string with an underscore and vice versa.
    
    Args:
    s (str): The input string to be processed.
    
    Returns:
    str: The processed string with spaces replaced.
    """
    # Replace spaces with underscores
    s = s.replace(' ', '_')
    # Replace underscores with spaces
    s = s.replace('_', ' ')
    return s
