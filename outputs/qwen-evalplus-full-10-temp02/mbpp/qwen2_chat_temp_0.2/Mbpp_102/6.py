def snake_to_camel(snake_str):
    """
    Convert a snake case string to camel case string.
    
    Args:
    snake_str (str): The snake case string to be converted.
    
    Returns:
    str: The camel case string.
    """
    # Split the string by underscores and capitalize the first letter of each word
    camel_str = ''.join(word.capitalize() for word in snake_str.split('_'))
    return camel_str
