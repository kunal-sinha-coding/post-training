def add_string(lst, format_string):
    """
    Apply a given format string to all of the elements in a list.
    
    Parameters:
    lst (list): The list of elements to be formatted.
    format_string (str): The format string to apply.
    
    Returns:
    list: A new list with the format string applied to each element.
    """
    # Apply the format string to each element in the list
    formatted_list = [format_string.format(element) for element in lst]
    return formatted_list
