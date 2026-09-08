def check_min_heap(arr):
    """
    Check if the given array represents min heap or not.
    
    Args:
    arr (list): The array to check.
    
    Returns:
    bool: True if the array is a min heap, False otherwise.
    """
    # Check if the array is empty
    if not arr:
        return True
    
    # Find the index of the largest element
    largest_index = arr.index(max(arr))
    
    # Check if the largest element is at the end of the array
    if largest_index == len(arr) - 1:
        return True
    
    # Check if the array is not a min heap
    for i in range(len(arr)):
        # Check if the current element is greater than the largest element
        if arr[i] > arr[largest_index]:
            return False
    
    return True