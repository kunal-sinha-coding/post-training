def count_samepair(list1, list2, list3):
    # Initialize a counter for identical pairs
    count = 0
    # Iterate through each pair of elements in the three lists
    for i in range(len(list1)):
        # Check if the current element in list1 is equal to the current element in list2
        if list1[i] == list2[i]:
            # Increment the counter if they are identical
            count += 1
    # Return the total count of identical pairs
    return count