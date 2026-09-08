def count_samepair(list1, list2, list3):
    # Initialize a counter for identical elements
    count = 0
    
    # Iterate through each pair of elements in the three lists
    for i in range(len(list1)):
        # Check if the current element in list1 is the same as the element at the same position in list2
        if list1[i] == list2[i]:
            # Increment the counter if the elements are identical
            count += 1
    
    # Return the counter of identical elements
    return count