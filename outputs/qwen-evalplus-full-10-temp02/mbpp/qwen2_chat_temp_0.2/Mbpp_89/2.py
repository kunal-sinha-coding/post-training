def closest_num(n):
    # Initialize the minimum value to a large number
    min_val = float('inf')
    # Iterate through the numbers from 1 to n-1
    for i in range(1, n):
        # Check if the current number is smaller than the minimum value found so far
        if i < min_val:
            # Update min_val with the current number
            min_val = i
    # Return the minimum value found
    return min_val