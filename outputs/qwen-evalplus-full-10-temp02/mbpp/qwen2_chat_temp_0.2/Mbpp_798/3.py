def _sum(arr):
    """
    Calculate the sum of an array.
    
    Args:
    arr (list): The input array of integers.
    
    Returns:
    int: The sum of the array elements.
    """
    total = 0
    for num in arr:
        total += num
    return total