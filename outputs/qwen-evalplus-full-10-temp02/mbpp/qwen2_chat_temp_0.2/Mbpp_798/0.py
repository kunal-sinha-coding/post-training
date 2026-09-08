def _sum(arr):
    """
    Calculate the sum of an array.
    
    Parameters:
    arr (list): A list of integers.
    
    Returns:
    int: The sum of the array.
    """
    total = 0
    for num in arr:
        total += num
    return total