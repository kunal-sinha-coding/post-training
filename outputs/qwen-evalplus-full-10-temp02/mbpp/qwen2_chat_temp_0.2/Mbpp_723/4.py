def count_same_pair(list1, list2):
    # Initialize a counter for the number of matching pairs
    count = 0
    # Iterate through each element in the first list
    for i in range(len(list1)):
        # Check if the current element in the first list matches the current element in the second list
        if list1[i] == list2[i]:
            # Increment the counter if they match
            count += 1
    # Return the total count of matching pairs
    return count