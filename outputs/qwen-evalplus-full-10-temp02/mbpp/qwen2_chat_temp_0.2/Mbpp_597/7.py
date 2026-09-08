def find_kth(arr1, arr2, k):
    # Initialize pointers for both arrays
    i, j = 0, 0
    
    # Initialize a variable to store the kth element
    result = 0
    
    # Iterate until k is less than the length of the larger array
    while k > 0:
        # If both arrays have elements left, choose the larger one
        if i < len(arr1) and j < len(arr2):
            if arr1[i] > arr2[j]:
                result = arr2[j]
                j += 1
            else:
                result = arr1[i]
                i += 1
        # If only one array has elements left, choose the remaining array
        elif i < len(arr1):
            result = arr1[i]
            i += 1
        else:
            result = arr2[j]
            j += 1
        
        # Decrement k
        k -= 1
    
    return result