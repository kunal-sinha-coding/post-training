def get_median(list1, list2, n):
    # Sort both lists
    list1.sort()
    list2.sort()
    
    # Initialize pointers for both lists
    i, j = 0, 0
    
    # Initialize the median
    median = 0
    
    # Iterate through both lists
    while i < n and j < n:
        # If both lists have elements, take the minimum of the two
        if list1[i] <= list2[j]:
            median = list1[i]
            i += 1
        else:
            median = list2[j]
            j += 1
    
    # If there are remaining elements in list1, take the last one
    if i < n:
        median = list1[i]
    
    # If there are remaining elements in list2, take the last one
    if j < n:
        median = list2[j]
    
    # Return the median
    return median