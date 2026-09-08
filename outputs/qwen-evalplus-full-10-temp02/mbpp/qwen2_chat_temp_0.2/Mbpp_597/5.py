def find_kth(arr1, arr2, k):
    # Initialize two pointers for the two arrays
    i, j = 0, 0
    # Initialize a variable to store the result
    result = 0
    
    # Iterate until one of the arrays is exhausted
    while i < len(arr1) and j < len(arr2):
        # Compare the elements at the current pointers
        if arr1[i] < arr2[j]:
            result = arr1[i]
            i += 1
        else:
            result = arr2[j]
            j += 1
    
    # If one of the arrays is exhausted, add the remaining elements to the result
    if i < len(arr1):
        result += arr1[i]
    elif j < len(arr2):
        result += arr2[j]
    
    return result
