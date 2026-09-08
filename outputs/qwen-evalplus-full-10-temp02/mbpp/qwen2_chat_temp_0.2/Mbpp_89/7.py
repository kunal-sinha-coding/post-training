def closest_num(n):
    # Initialize the minimum difference to a large number
    min_diff = float('inf')
    # Initialize the closest number to a large number
    closest_num = float('inf')
    # Iterate through the numbers from 1 to n-1
    for i in range(1, n):
        # Calculate the difference between the current number and the closest number
        diff = abs(i - closest_num)
        # Update the minimum difference and closest number if the current difference is smaller
        if diff < min_diff:
            min_diff = diff
            closest_num = i
    # Return the closest number
    return closest_num