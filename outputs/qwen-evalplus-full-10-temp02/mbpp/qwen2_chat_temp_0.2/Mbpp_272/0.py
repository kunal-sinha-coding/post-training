def rear_extract(tuples_list):
    # Initialize an empty list to store the rear elements
    rear_elements = []
    # Iterate over each tuple in the list
    for tup in tuples_list:
        # Append the last element of the tuple to the rear_elements list
        rear_elements.append(tup[-1])
    # Return the list of rear elements
    return rear_elements