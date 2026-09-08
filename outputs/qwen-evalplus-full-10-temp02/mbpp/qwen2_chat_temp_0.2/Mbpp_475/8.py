def sort_counter(counter):
    """
    Sorts a dictionary by value in ascending order.
    
    Parameters:
    counter (dict): A dictionary to be sorted.
    
    Returns:
    list: A list of tuples, where each tuple contains a key-value pair from the dictionary.
    """
    sorted_counter = sorted(counter.items(), key=lambda item: item[1])
    return sorted_counter
