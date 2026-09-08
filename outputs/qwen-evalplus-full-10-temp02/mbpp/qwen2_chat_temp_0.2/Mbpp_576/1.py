def is_Sub_Array(arr, b):
    """
    Check if arr is a sublist of b.
    
    Parameters:
    arr (list): The list to check.
    b (list): The list to compare against.
    
    Returns:
    bool: True if arr is a sublist of b, False otherwise.
    """
    # Check if arr is empty or b is empty
    if not arr or not b:
        return False
    
    # Iterate through b to check if arr is a sublist
    for i in range(len(b)):
        # Check if the current element of b matches the current element of arr
        if b[i] == arr[i]:
            # If all elements match, return True
            return True
    
    # If no match is found, return False
    return False