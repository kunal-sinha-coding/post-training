def extract_rear(string_tuple):
    """
    Extracts the rear index element of each string in the given tuple.
    
    Parameters:
    string_tuple (tuple): A tuple containing strings.
    
    Returns:
    list: A list containing the rear index elements of each string.
    """
    # Extracting the rear index elements from each string in the tuple
    rear_elements = [string_tuple[i][-1] for i in range(len(string_tuple))]
    return rear_elements
