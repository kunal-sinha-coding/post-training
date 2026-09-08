def find_kth(arr1, arr2, k):
    # Sort both arrays
    arr1.sort()
    arr2.sort()
    
    # Initialize pointers for both arrays
    i, j = 0, 0
    
    # Initialize a variable to store the kth element
    result = 0
    
    # Iterate until k is less than the length of the arrays
    while k > 0:
        # If the current element in arr1 is less than or equal to the current element in arr2
        if i < len(arr1) and j < len(arr2):
            if arr1[i] <= arr2[j]:
                result = arr1[i]
                i += 1
            else:
                result = arr2[j]
                j += 1
        # If the current element in arr1 is greater than the current element in arr2
        elif i < len(arr1):
            result = arr1[i]
            i += 1
        # If the current element in arr2 is greater than the current element in arr1
        elif j < len(arr2):
            result = arr2[j]
            j += 1
        # If k is 0, return the result
        k -= 1
    
    return result