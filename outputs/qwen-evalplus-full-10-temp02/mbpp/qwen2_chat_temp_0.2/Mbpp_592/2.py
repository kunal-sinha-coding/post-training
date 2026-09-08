def sum_Of_product(n):
    # Initialize the sum to 0
    sum_product = 0
    # Iterate through the range of n
    for i in range(1, n + 1):
        # Calculate the binomial coefficient
        binomial_coefficient = (n - i + 1) * (n - i) // 2
        # Multiply the binomial coefficient with the sum_product
        sum_product += binomial_coefficient
    return sum_product