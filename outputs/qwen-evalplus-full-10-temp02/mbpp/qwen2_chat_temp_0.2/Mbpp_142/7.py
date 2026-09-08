def count_samepair(list1, list2, list3):
    # Initialize a counter for identical pairs
    identical_pairs = 0
    
    # Iterate through each pair of elements in the three lists
    for i in range(len(list1)):
        # Check if the current pair of elements is identical in the same position
        if list1[i] == list2[i] == list3[i]:
            identical_pairs += 1
    
    # Return the total count of identical pairs
    return identical_pairs