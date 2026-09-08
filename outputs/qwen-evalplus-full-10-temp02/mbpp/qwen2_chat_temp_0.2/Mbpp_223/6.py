def is_majority(arr, n, x):
    """
    Check if the element x is the majority element in the sorted array arr of length n.
    
    Parameters:
    arr (list): The sorted array.
    n (int): The length of the array.
    x (int): The element to check.
    
    Returns:
    bool: True if x is the majority element, False otherwise.
    """
    count = 0
    for i in range(n):
        if arr[i] == x:
            count += 1
    return count > n // 2
