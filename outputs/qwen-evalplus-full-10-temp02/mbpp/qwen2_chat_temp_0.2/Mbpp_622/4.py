def get_median(list1, list2, n):
    # Sort both lists
    list1.sort()
    list2.sort()
    
    # Initialize pointers for both lists
    i, j = 0, 0
    
    # Initialize the median
    median = 0
    
    # Calculate the median
    while i < n and j < n:
        if list1[i] < list2[j]:
            median = list1[i]
            i += 1
        else:
            median = list2[j]
            j += 1
    
    # Check if the number of elements is odd
    if n % 2 == 1:
        return median
    else:
        # Calculate the average of the two middle elements
        return (median + list1[i]) / 2