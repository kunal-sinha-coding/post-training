def reverse_string_list(string_list):
    """
    Reverses each string in the given list of string values.
    
    Args:
    string_list (list): A list of strings to be reversed.
    
    Returns:
    list: A new list with each string reversed.
    """
    # Using list comprehension to reverse each string in the list
    reversed_list = [s[::-1] for s in string_list]
    return reversed_list
