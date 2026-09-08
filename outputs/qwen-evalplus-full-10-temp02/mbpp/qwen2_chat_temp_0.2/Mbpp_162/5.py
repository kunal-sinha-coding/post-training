def sum_series(n):
    # Initialize the sum to 0
    total_sum = 0
    
    # Loop through the range from 0 to n // 2
    for i in range(n // 2):
        # Calculate the sum for the current i
        current_sum = i * (n - 2 * i)
        # Add the current sum to the total sum
        total_sum += current_sum
    
    return total_sum