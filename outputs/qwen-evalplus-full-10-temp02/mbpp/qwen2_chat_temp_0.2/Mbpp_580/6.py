def extract_even(mixed_tuple):
    """
    Remove uneven elements from the nested mixed tuple.
    
    Args:
    mixed_tuple (tuple): A nested tuple containing mixed data types.
    
    Returns:
    tuple: A tuple with all even elements removed.
    """
    # Use list comprehension to filter out even elements
    even_elements = [element for element in mixed_tuple if isinstance(element, int) and element % 2 == 0]
    return tuple(even_elements)
