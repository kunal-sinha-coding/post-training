def cube_Sum(n):
    # Initialize the sum of cubes
    total_sum = 0
    # Loop through the first n even natural numbers
    for i in range(2, n + 1, 2):
        # Add the cube of the current even number to the total sum
        total_sum += i ** 3
    # Return the total sum of cubes
    return total_sum