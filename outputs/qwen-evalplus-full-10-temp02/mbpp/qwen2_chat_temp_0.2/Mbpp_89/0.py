def closest_num(n):
    # Initialize the closest number to n as n itself
    closest = n
    # Iterate through the numbers from 1 to n-1
    for i in range(1, n):
        # Check if the current number is smaller than the closest number
        if i < closest:
            closest = i
    # Return the closest number
    return closest