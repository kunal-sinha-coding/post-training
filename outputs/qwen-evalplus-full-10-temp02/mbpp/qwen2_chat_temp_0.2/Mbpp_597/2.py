def find_kth(arr1, arr2, k):
    # Initialize two pointers for the two arrays
    i, j = 0, 0
    # Initialize a variable to store the kth element
    kth_element = 0
    
    # Iterate until one of the pointers reaches the end of their respective arrays
    while i < len(arr1) and j < len(arr2):
        # If the current element in arr1 is greater than the current element in arr2, move the pointer in arr2
        if arr1[i] > arr2[j]:
            j += 1
        # If the current element in arr1 is less than the current element in arr2, move the pointer in arr1
        else:
            i += 1
        # If k is 0, return the kth element
        if k == 0:
            return arr1[i]
        # Decrease k by 1
        k -= 1
    
    # If k is greater than the length of arr1, return the kth element from arr2
    if k > 0:
        return arr2[j]
    # If k is less than the length of arr2, return the kth element from arr1
    return arr1[i]