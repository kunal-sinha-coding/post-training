def extract_rear(string_tuple):
    """
    Extracts only the rear index element of each string in the given tuple.
    
    Args:
    string_tuple (tuple): A tuple containing strings.
    
    Returns:
    list: A list containing the rear index elements of each string.
    """
    # Extracting the rear index elements of each string
    rear_index_elements = [string_tuple[i][-1] for i in range(len(string_tuple))]
    return rear_index_elements
