def find_kth(arr1, arr2, k):
    # Initialize two pointers for the two arrays
    i, j = 0, 0
    
    # Initialize a counter for the kth element
    count = 0
    
    # Iterate until k is reached or one of the arrays is exhausted
    while count < k:
        # If the current element in arr1 is less than or equal to the current element in arr2, add it to the count
        if arr1[i] <= arr2[j]:
            count += 1
            i += 1
        # If the current element in arr1 is greater than the current element in arr2, add it to the count
        else:
            count += 1
            j += 1
    
    # Return the kth element
    return arr1[i] if i < len(arr1) else arr2[j]