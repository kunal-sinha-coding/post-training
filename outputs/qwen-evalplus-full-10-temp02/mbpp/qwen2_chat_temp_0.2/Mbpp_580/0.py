def extract_even(mixed_tuple):
    """
    This function takes a nested mixed tuple as input and returns a new tuple containing only the even elements.
    
    Parameters:
    mixed_tuple (tuple): A tuple containing elements of various data types.
    
    Returns:
    tuple: A tuple containing only the even elements from the input tuple.
    """
    # Initialize an empty list to store even elements
    even_elements = []
    
    # Iterate through each element in the input tuple
    for element in mixed_tuple:
        # Check if the element is an integer and even
        if isinstance(element, int) and element % 2 == 0:
            # Append the even element to the list
            even_elements.append(element)
    
    # Return the list of even elements
    return tuple(even_elements)
