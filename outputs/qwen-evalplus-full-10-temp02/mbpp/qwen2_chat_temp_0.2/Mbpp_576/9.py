def is_Sub_Array(arr1, arr2):
    """
    Check if arr2 is a sublist of arr1.
    
    Parameters:
    arr1 (list): The main list.
    arr2 (list): The sublist to check.
    
    Returns:
    bool: True if arr2 is a sublist of arr1, False otherwise.
    """
    # Check if arr2 is empty
    if not arr2:
        return True
    
    # Iterate through arr1
    for i in range(len(arr1)):
        # Check if the current element of arr1 matches the first element of arr2
        if arr1[i] == arr2[0]:
            # Check if the rest of arr2 matches the remaining elements of arr1
            if arr2[1:] == arr1[i+1:]:
                return True
    return False