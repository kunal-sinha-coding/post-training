def is_majority(arr, n, x):
    """
    Check if the given element x is the majority element in the sorted array arr.
    
    Parameters:
    arr (list): The sorted array.
    n (int): The length of the array.
    x (int): The element to check.
    
    Returns:
    bool: True if x is the majority element, False otherwise.
    """
    # Initialize the count of the majority element
    count = 0
    
    # Iterate through the array
    for i in range(n):
        # If the current element is equal to x, increment the count
        if arr[i] == x:
            count += 1
    
    # Check if the count is greater than n/2
    return count > n // 2
