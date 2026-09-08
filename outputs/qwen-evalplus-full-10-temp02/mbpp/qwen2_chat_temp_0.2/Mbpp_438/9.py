def count_bidirectional(test_list):
    # Initialize a counter for bidirectional tuple pairs
    bidirectional_count = 0
    
    # Iterate through the list of tuples
    for i in range(len(test_list)):
        # Iterate through the rest of the list starting from the current index
        for j in range(i + 1, len(test_list)):
            # Check if the current tuple and the next tuple are bidirectional
            if test_list[i] == test_list[j]:
                bidirectional_count += 1
    
    # Return the total count of bidirectional tuple pairs
    return bidirectional_count