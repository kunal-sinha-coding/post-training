def sum_Of_product(n):
    # Initialize the sum to 0
    sum_product = 0
    # Iterate through the first n+1 terms of the binomial coefficients
    for i in range(n + 1):
        # Calculate the binomial coefficient for the current term
        binomial_coefficient = (n + 1) // i
        # Multiply the binomial coefficient by the current term's index
        sum_product += binomial_coefficient * i
    return sum_product