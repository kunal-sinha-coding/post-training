def count_samepair(list1, list2, list3):
    # Initialize a counter for the number of identical pairs
    count = 0
    
    # Iterate through each pair of elements in the three lists
    for i in range(len(list1)):
        # Check if the current pair of elements is identical in the same position
        if list1[i] == list2[i] == list3[i]:
            # Increment the counter if the pair is identical
            count += 1
    
    # Return the total count of identical pairs
    return count