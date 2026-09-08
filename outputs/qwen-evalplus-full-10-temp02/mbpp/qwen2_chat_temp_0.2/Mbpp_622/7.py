def get_median(list1, list2, size):
    # Sort both lists
    list1.sort()
    list2.sort()
    
    # Calculate the median
    mid1 = size // 2
    mid2 = size // 2 + 1
    
    # If size is odd, the median is the middle element
    if size % 2 == 1:
        median = list1[mid1]
    else:
        # If size is even, the median is the average of the two middle elements
        median = (list1[mid1] + list2[mid2]) / 2
    
    return median