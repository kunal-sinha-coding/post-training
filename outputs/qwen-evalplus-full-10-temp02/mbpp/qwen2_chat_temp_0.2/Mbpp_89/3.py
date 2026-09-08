def closest_num(n):
    # Initialize the closest number to a large value
    closest = float('inf')
    # Iterate through the numbers from 1 to n-1
    for i in range(1, n):
        # Check if the current number is smaller than the closest number found so far
        if i < closest:
            closest = i
    return closest