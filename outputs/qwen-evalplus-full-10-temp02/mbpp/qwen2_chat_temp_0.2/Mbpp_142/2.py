def count_samepair(list1, list2, list3):
    # Initialize a counter for identical pairs
    count = 0
    # Iterate through each pair of elements in the first list
    for i in range(len(list1)):
        # Check if the current element in the first list is the same as the current element in the second list
        if list1[i] == list2[i]:
            # Increment the counter if they are the same
            count += 1
    # Return the total count of identical pairs
    return count