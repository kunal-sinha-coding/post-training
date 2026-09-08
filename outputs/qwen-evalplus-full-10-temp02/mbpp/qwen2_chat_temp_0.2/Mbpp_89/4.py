def closest_num(n):
    # Initialize the closest number to the largest possible integer
    closest = n - 1
    # Iterate through the numbers from n-1 down to 1
    for i in range(n - 1, 0, -1):
        # Check if the current number is smaller than the closest number
        if i < closest:
            closest = i
    return closest