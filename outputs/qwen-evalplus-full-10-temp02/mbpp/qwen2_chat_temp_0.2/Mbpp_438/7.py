def count_bidirectional(tuples_list):
    # Initialize a counter for bidirectional tuple pairs
    bidirectional_count = 0
    
    # Iterate through the list of tuples
    for i in range(len(tuples_list)):
        # Iterate through the rest of the list starting from the next element
        for j in range(i + 1, len(tuples_list)):
            # Check if the current tuple is bidirectional
            if tuples_list[i][0] == tuples_list[j][1] and tuples_list[i][1] == tuples_list[j][0]:
                # Increment the counter if it is bidirectional
                bidirectional_count += 1
    
    # Return the total count of bidirectional tuple pairs
    return bidirectional_count