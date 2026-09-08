import math

def zero_count(arr):
    """
    Calculate the ratio of zeroes to non-zeroes in an array of integers.
    
    Parameters:
    arr (list): A list of integers.
    
    Returns:
    float: The ratio of zeroes to non-zeroes.
    """
    # Count the number of zeroes in the array
    zeroes = sum(1 for num in arr if num == 0)
    # Count the number of non-zeroes in the array
    non_zeroes = len(arr) - zeroes
    # Calculate the ratio of zeroes to non-zeroes
    ratio = zeroes / non_zeroes
    return ratio
