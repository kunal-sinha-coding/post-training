def count_bidirectional(test_list):
    # Initialize a counter for bidirectional tuple pairs
    bidirectional_count = 0
    
    # Iterate through the list of tuples
    for i in range(len(test_list)):
        # Iterate through the list of tuples again
        for j in range(i + 1, len(test_list)):
            # Check if the current tuple is bidirectional
            if test_list[i][0] == test_list[j][1] and test_list[j][0] == test_list[i][1]:
                # Increment the counter if it is bidirectional
                bidirectional_count += 1
    
    # Return the total count of bidirectional tuple pairs
    return bidirectional_count