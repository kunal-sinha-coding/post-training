def get_median(list1, list2, n):
    # Sort both lists
    list1.sort()
    list2.sort()
    
    # Calculate the median
    if n % 2 == 1:
        # If odd, return the middle element
        median = list1[n // 2]
    else:
        # If even, return the average of the two middle elements
        median = (list1[n // 2 - 1] + list1[n // 2]) / 2
    
    return median