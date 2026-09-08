def snake_to_camel(snake_str):
    """
    Convert a snake case string to camel case string.
    
    Args:
    snake_str (str): The snake case string to be converted.
    
    Returns:
    str: The camel case string.
    """
    # Split the snake case string into words
    words = snake_str.split('_')
    # Capitalize the first letter of each word except the first one
    camel_case_str = words[0].capitalize() + ''.join(word.capitalize() for word in words[1:])
    return camel_case_str
