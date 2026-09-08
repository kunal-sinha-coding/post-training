def sum_Of_product(n):
    # Initialize the sum to 0
    sum = 0
    # Iterate through the range from 1 to n
    for i in range(1, n + 1):
        # Calculate the binomial coefficient C(i, j) using the formula C(i, j) = i! / (j! * (i - j)!)
        binomial_coefficient = i * (i - 1) // (i - j)
        # Multiply the binomial coefficient by the product of consecutive binomial coefficients
        sum += binomial_coefficient * (i - 1)
    return sum