import math

def zero_count(arr):
    """
    Calculate the ratio of zeroes to non-zeroes in an array of integers.
    
    Parameters:
    arr (list): A list of integers.
    
    Returns:
    float: The ratio of zeroes to non-zeroes.
    """
    # Count the number of zeroes and non-zeroes in the array
    zeroes = sum(1 for num in arr if num == 0)
    non_zeroes = sum(1 for num in arr if num != 0)
    
    # Calculate the ratio of zeroes to non-zeroes
    ratio = zeroes / non_zeroes
    
    # Return the ratio rounded to 10 decimal places
    return round(ratio, 10)
