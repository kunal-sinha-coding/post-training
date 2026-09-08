def sort_counter(counter):
    """
    Sorts a dictionary by value in ascending order.
    
    Parameters:
    counter (dict): A dictionary with keys as strings and values as integers.
    
    Returns:
    list: A list of tuples, where each tuple contains a key-value pair from the dictionary.
    """
    # Sort the dictionary by values in ascending order
    sorted_counter = sorted(counter.items(), key=lambda item: item[1])
    return sorted_counter
