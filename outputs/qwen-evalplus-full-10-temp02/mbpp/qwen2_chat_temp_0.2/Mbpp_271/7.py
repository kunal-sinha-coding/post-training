def even_Power_Sum(n):
    # Initialize the sum to 0
    sum = 0
    # Loop through the first n even natural numbers
    for i in range(2, n + 1, 2):
        # Calculate the fifth power of the current even number
        power = i ** 5
        # Add the power to the sum
        sum += power
    # Return the final sum
    return sum