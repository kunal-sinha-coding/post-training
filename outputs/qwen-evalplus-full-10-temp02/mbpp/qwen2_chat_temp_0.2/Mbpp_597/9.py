def find_kth(arr1, arr2, k):
    # Initialize two pointers for the two arrays
    i, j = 0, 0
    # Initialize a counter for the kth element
    count = 0
    
    # Iterate until the end of either array is reached
    while i < len(arr1) and j < len(arr2):
        # If the current element in arr1 is less than the current element in arr2
        if arr1[i] < arr2[j]:
            # Increment the counter and move the pointer in arr1
            count += 1
            i += 1
        # If the current element in arr1 is greater than the current element in arr2
        else:
            # Increment the counter and move the pointer in arr2
            count += 1
            j += 1
    
    # If k is greater than the length of arr1, return the kth element in arr2
    if k > len(arr1):
        return arr2[k - len(arr1)]
    # If k is greater than the length of arr2, return the kth element in arr1
    elif k > len(arr2):
        return arr1[k - len(arr2)]
    # If k is equal to the length of arr1, return the kth element in arr1
    else:
        return arr1[k - 1]