def _sum(arr):
    """
    Calculate the sum of an array.
    
    Parameters:
    arr (list): A list of integers.
    
    Returns:
    int: The sum of the array elements.
    """
    total_sum = 0
    for num in arr:
        total_sum += num
    return total_sum