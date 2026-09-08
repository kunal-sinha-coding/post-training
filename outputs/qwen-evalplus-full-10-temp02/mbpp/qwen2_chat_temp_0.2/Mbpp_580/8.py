def extract_even(mixed_tuple):
    """
    Remove uneven elements from the nested mixed tuple.
    
    Parameters:
    mixed_tuple (tuple): A tuple containing nested mixed types.
    
    Returns:
    tuple: A tuple with all uneven elements removed.
    """
    # Initialize an empty list to store even elements
    even_elements = []
    
    # Iterate through each element in the mixed tuple
    for element in mixed_tuple:
        # Check if the element is an integer
        if isinstance(element, int):
            # Append the integer to the even_elements list
            even_elements.append(element)
        # Check if the element is a tuple
        elif isinstance(element, tuple):
            # Recursively call the function on the tuple
            even_elements.extend(extract_even(element))
    
    # Return the list of even elements
    return even_elements
