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
        # Check if arr2 is a prefix of arr1 starting from index i
        if arr1[i:i+len(arr2)] == arr2:
            return True
    return False
