def count_same_pair(list1, list2):
    # Initialize a counter for the number of matching pairs
    count = 0
    
    # Iterate through each element in the first list
    for i in range(len(list1)):
        # Check if the current element is present in the second list
        if list1[i] in list2:
            # Increment the counter if the elements are the same
            count += 1
    
    # Return the total count of matching pairs
    return count