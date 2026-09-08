def rear_extract(tuples_list):
    """
    Extracts the rear element of each tuple in the given list.
    
    Parameters:
    tuples_list (list of tuples): A list of tuples.
    
    Returns:
    list: A list containing the rear element of each tuple.
    """
    # Initialize an empty list to store the rear elements
    rear_elements = []
    # Iterate over each tuple in the list
    for tuple_ in tuples_list:
        # Append the last element of the tuple to the rear_elements list
        rear_elements.append(tuple_[2])
    # Return the list of rear elements
    return rear_elements
