def get_median(list1, list2, size):
    # Sort both lists
    list1.sort()
    list2.sort()
    
    # Calculate the middle index
    mid = size // 2
    
    # If size is odd, return the middle element
    if size % 2 == 1:
        return list1[mid]
    
    # If size is even, return the average of the two middle elements
    else:
        return (list1[mid - 1] + list1[mid]) / 2.0