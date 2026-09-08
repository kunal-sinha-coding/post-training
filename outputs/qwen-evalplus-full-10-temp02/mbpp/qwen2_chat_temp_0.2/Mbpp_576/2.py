def is_Sub_Array(arr1, arr2):
    """
    Check if arr2 is a sublist of arr1.
    
    Parameters:
    arr1 (list): The main list.
    arr2 (list): The sublist to check.
    
    Returns:
    bool: True if arr2 is a sublist of arr1, False otherwise.
    """
    # Iterate through arr1 to check if arr2 is a sublist
    for i in range(len(arr1)):
        # Check if the current element of arr1 matches the current element of arr2
        if arr1[i] == arr2[i]:
            # If it matches, move to the next element in arr1
            continue
        # If it doesn't match, return False
        return False
    # If all elements match, return True
    return True