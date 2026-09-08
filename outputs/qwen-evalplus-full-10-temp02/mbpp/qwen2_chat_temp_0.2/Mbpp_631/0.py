def replace_spaces(text):
    """
    Replace whitespaces in the given string with an underscore and vice versa.
    
    Args:
    text (str): The input string to be processed.
    
    Returns:
    str: The processed string with spaces replaced.
    """
    # Replace spaces with underscores
    result = text.replace(' ', '_')
    # Replace underscores with spaces
    result = result.replace('_', ' ')
    return result
