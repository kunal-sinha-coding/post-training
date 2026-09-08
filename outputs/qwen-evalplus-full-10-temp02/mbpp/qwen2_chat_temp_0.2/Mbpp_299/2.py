def max_aggregate(tuples_list):
    # Initialize the maximum value with the first tuple in the list
    max_value = tuples_list[0]
    
    # Iterate through each tuple in the list
    for tuple in tuples_list:
        # Update the maximum value if the current tuple's value is greater
        if tuple[1] > max_value:
            max_value = tuple[1]
    
    # Return the maximum value found
    return max_value