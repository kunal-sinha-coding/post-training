def extract_even(mixed_tuple):
    """
    Remove uneven elements from the nested mixed tuple.
    
    Parameters:
    mixed_tuple (tuple): A nested mixed tuple containing elements of various types.
    
    Returns:
    tuple: A tuple with all uneven elements removed.
    """
    # Use list comprehension to filter out odd elements
    even_elements = [element for element in mixed_tuple if isinstance(element, int) and element % 2 == 0]
    # Return the filtered tuple
    return tuple(even_elements)
