def count_same_pair(list1, list2):
    # Initialize a counter for matching pairs
    count = 0
    
    # Iterate through each pair of elements in the lists
    for i in range(len(list1)):
        # Check if the elements at the current index in both lists are the same
        if list1[i] == list2[i]:
            count += 1
    
    # Return the count of matching pairs
    return count