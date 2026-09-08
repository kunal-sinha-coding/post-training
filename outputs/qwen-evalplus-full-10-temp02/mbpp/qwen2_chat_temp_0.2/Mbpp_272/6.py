def rear_extract(tuples_list):
    """
    Extracts the rear element from each tuple in the provided list and returns a new list with these elements.
    
    Parameters:
    tuples_list (list of tuples): A list containing tuples.
    
    Returns:
    list of tuples: A list containing the rear elements of each tuple.
    """
    # Initialize an empty list to store the rear elements
    rear_elements = []
    
    # Iterate over each tuple in the input list
    for tup in tuples_list:
        # Extract the rear element using the last index
        rear_elements.append(tup[-1])
    
    # Return the list of rear elements
    return rear_elements