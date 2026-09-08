def sum_series(n):
    """
    Calculate the sum (n - 2*i) from i=0 to n // 2, for instance n + (n-2) + (n-4)... (until n-x =< 0).
    
    Args:
    n (int): The upper limit of the series.
    
    Returns:
    int: The sum of the series.
    """
    # Initialize the sum
    total_sum = 0
    
    # Iterate from 0 to n // 2
    for i in range(n // 2):
        # Calculate the sum for the current i
        current_sum = (n - 2 * i)
        # Add the current sum to the total sum
        total_sum += current_sum
    
    return total_sum