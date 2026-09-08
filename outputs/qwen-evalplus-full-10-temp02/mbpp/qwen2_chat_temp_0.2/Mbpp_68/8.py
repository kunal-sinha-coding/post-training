def is_Monotonic(arr):
    """
    Check if the given array is monotonic or not.
    
    Args:
    arr (list): The array to check.
    
    Returns:
    bool: True if the array is monotonic, False otherwise.
    """
    # Check if the array is empty or has only one element
    if len(arr) <= 1:
        return True
    
    # Determine the direction of monotonicity
    increasing = decreasing = True
    
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        if arr[i] > arr[i - 1]:
            decreasing = False
        elif arr[i] < arr[i - 1]:
            increasing = False
    
    # If both directions are True, the array is monotonic
    return increasing or decreasing