def find_kth(arr1, arr2, k):
    # Initialize two pointers for the two arrays
    i, j = 0, 0
    
    # Initialize a counter for the kth element
    count = 0
    
    # Iterate until we find the kth element
    while count < k:
        # If the current element in arr1 is less than or equal to the current element in arr2
        if arr1[i] <= arr2[j]:
            # Increment the counter and move the pointer in arr1
            count += 1
            i += 1
        # If the current element in arr1 is greater than the current element in arr2
        else:
            # Increment the counter and move the pointer in arr2
            count += 1
            j += 1
    
    # Return the kth element from arr1
    return arr1[i - 1]