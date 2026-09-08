def extract_even(mixed_tuple):
    """
    Extract even elements from a nested mixed tuple.
    
    Parameters:
    mixed_tuple (tuple): A nested tuple containing elements of various types.
    
    Returns:
    tuple: A tuple containing only the even elements from the nested tuple.
    """
    # Initialize an empty list to store even elements
    even_elements = []
    
    # Iterate over each element in the mixed tuple
    for element in mixed_tuple:
        # Check if the element is an integer
        if isinstance(element, int):
            # Check if the integer is even
            if element % 2 == 0:
                # Append the even integer to the list
                even_elements.append(element)
    
    # Return the list of even elements
    return tuple(even_elements)
