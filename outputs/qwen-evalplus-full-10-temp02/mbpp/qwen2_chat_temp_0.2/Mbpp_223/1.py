def is_majority(arr, n, x):
    """
    Check if the element x is the majority element in the given sorted array arr.
    
    Parameters:
    arr (list): The sorted array.
    n (int): The length of the array.
    x (int): The element to check for.
    
    Returns:
    bool: True if x is the majority element, False otherwise.
    """
    # Count the occurrences of x in the array
    count = arr.count(x)
    
    # Check if the count is greater than n/2
    return count > n // 2
