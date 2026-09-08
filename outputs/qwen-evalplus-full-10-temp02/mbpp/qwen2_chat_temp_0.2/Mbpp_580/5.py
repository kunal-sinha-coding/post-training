def extract_even(mixed_tuple):
    """
    Remove uneven elements from the nested mixed tuple.
    
    Args:
    mixed_tuple (tuple): A nested tuple containing elements of various types.
    
    Returns:
    tuple: A tuple with all elements removed that are not even.
    """
    # Initialize an empty list to store even elements
    even_elements = []
    
    # Iterate over each element in the mixed_tuple
    for element in mixed_tuple:
        # Check if the element is an even number
        if isinstance(element, int) and element % 2 == 0:
            # If it is even, add it to the even_elements list
            even_elements.append(element)
    
    # Return the list of even elements
    return tuple(even_elements)
