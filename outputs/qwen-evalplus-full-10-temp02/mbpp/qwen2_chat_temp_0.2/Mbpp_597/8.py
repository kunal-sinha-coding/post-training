def find_kth(arr1, arr2, k):
    # Initialize two pointers for the two arrays
    i, j = 0, 0
    # Initialize a variable to store the kth element
    kth_element = 0
    
    # Iterate until k is less than the length of the arrays
    while k > 0:
        # If the current element in arr1 is less than or equal to the current element in arr2
        if arr1[i] <= arr2[j]:
            # Add the current element from arr1 to kth_element
            kth_element += arr1[i]
            # Move the pointer in arr1 to the next element
            i += 1
        else:
            # Add the current element from arr2 to kth_element
            kth_element += arr2[j]
            # Move the pointer in arr2 to the next element
            j += 1
    
    # Return the kth element
    return kth_element