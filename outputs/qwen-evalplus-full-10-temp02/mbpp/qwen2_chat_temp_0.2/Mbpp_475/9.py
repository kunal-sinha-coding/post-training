def sort_counter(counter):
    """
    Sorts a dictionary by value in ascending order.
    
    Parameters:
    counter (dict): The dictionary to be sorted.
    
    Returns:
    list: A list of tuples, where each tuple contains a key-value pair from the dictionary.
    """
    # Sort the dictionary by values in ascending order
    sorted_counter = sorted(counter.items(), key=lambda x: x[1])
    return sorted_counter