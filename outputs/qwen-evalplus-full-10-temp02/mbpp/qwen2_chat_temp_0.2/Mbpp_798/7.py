def _sum(arr):
    """
    Calculate the sum of an array.
    
    Args:
    arr (list): The input array.
    
    Returns:
    int: The sum of the array.
    """
    total_sum = 0
    for num in arr:
        total_sum += num
    return total_sum