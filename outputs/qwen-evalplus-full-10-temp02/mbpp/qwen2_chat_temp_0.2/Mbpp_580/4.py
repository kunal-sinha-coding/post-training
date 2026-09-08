def extract_even(mixed_tuple):
    """
    Remove uneven elements from the nested mixed tuple.
    
    Args:
    mixed_tuple (tuple): A nested tuple containing elements of various types.
    
    Returns:
    tuple: A tuple with all even elements removed.
    """
    # Initialize an empty list to store even elements
    even_elements = []
    
    # Iterate through each element in the mixed_tuple
    for element in mixed_tuple:
        # Check if the element is an instance of int and even
        if isinstance(element, int) and element % 2 == 0:
            # Append the even element to the even_elements list
            even_elements.append(element)
    
    # Return the list of even elements
    return tuple(even_elements)
