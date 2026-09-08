def extract_even(mixed_tuple):
    """
    Remove uneven elements from the nested mixed tuple.
    
    Parameters:
    mixed_tuple (tuple): The input mixed tuple containing nested tuples and elements.
    
    Returns:
    tuple: A tuple with all even elements removed.
    """
    # Initialize an empty list to store even elements
    even_elements = []
    
    # Iterate over each element in the mixed tuple
    for element in mixed_tuple:
        # Check if the element is an integer
        if isinstance(element, int):
            # Check if the element is even
            if element % 2 == 0:
                # Append the even element to the list
                even_elements.append(element)
    
    # Join the list of even elements into a tuple and return it
    return tuple(even_elements)
