def is_Monotonic(arr):
    """
    Check if the given array is monotonic or not.
    
    Args:
    arr (list): A list of integers.
    
    Returns:
    bool: True if the array is monotonic, False otherwise.
    """
    increasing = decreasing = True
    
    for i in range(1, len(arr)):
        if arr[i] > arr[i - 1]:
            decreasing = False
        elif arr[i] < arr[i - 1]:
            increasing = False
    
    return increasing or decreasing