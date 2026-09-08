def rear_extract(tuples_list):
    """
    Extracts the rear element from each tuple in the provided list and returns a new list with these elements.
    
    Parameters:
    tuples_list (list of tuples): The input list of tuples.
    
    Returns:
    list: A list containing the rear elements of each tuple.
    """
    # Initialize an empty list to store the rear elements
    rear_elements = []
    
    # Iterate over each tuple in the input list
    for tuple_ in tuples_list:
        # Append the last element of the tuple to the rear_elements list
        rear_elements.append(tuple_[2])
    
    # Return the list of rear elements
    return rear_elements
