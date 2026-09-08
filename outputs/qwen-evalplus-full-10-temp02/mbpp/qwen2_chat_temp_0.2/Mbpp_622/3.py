def get_median(list1, list2, size):
    # Sort both lists
    list1.sort()
    list2.sort()
    
    # Calculate the median
    if size % 2 == 1:
        # If size is odd, return the middle element
        median = list1[size // 2]
    else:
        # If size is even, return the average of the two middle elements
        median = (list1[size // 2 - 1] + list1[size // 2]) / 2
    
    return median