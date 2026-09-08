def sum_Of_product(n):
    # Initialize the sum to 0
    sum_product = 0
    # Iterate through the range from 1 to n
    for i in range(1, n + 1):
        # Calculate the binomial coefficient C(i, j)
        binomial_coefficient = n // i
        # Multiply the binomial coefficient with the sum_product
        sum_product += binomial_coefficient
    # Return the final sum_product
    return sum_product