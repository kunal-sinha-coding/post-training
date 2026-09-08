def max_aggregate(tuples_list):
    # Initialize the maximum aggregate with the first tuple in the list
    max_aggregate = tuples_list[0]
    
    # Iterate through each tuple in the list
    for tuple in tuples_list:
        # Update the maximum aggregate if the current tuple's aggregate is greater
        if tuple[1] > max_aggregate[1]:
            max_aggregate = tuple
    
    # Return the maximum aggregate
    return max_aggregate