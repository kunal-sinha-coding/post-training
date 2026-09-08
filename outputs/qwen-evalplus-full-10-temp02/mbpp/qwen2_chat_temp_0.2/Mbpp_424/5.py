def extract_rear(string_tuple):
    """
    Extracts the rear index element of each string in the given tuple.
    
    Args:
    string_tuple (tuple): A tuple containing strings.
    
    Returns:
    list: A list containing the rear index elements of each string.
    """
    # Initialize an empty list to store the rear index elements
    rear_index_elements = []
    # Iterate over each string in the tuple
    for string in string_tuple:
        # Extract the rear index element using slicing
        rear_index = string[-1]
        # Append the rear index element to the list
        rear_index_elements.append(rear_index)
    # Return the list of rear index elements
    return rear_index_elements
