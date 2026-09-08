def get_median(list1, list2, n):
    # Sort both lists
    list1.sort()
    list2.sort()
    
    # Calculate the median
    mid1 = n // 2
    mid2 = n // 2 + 1
    
    # If the total number of elements is odd, return the middle element
    if n % 2 == 1:
        return list1[mid1]
    
    # If the total number of elements is even, return the average of the two middle elements
    else:
        return (list1[mid1] + list2[mid2]) / 2.0