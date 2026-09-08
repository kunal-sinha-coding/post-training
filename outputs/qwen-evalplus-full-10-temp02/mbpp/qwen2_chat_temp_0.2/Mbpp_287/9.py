def square_Sum(n):
    # Initialize the sum to 0
    sum = 0
    # Loop through the first n even natural numbers
    for i in range(2, n + 1, 2):
        # Add the square of the current even number to the sum
        sum += i ** 2
    # Return the final sum
    return sum