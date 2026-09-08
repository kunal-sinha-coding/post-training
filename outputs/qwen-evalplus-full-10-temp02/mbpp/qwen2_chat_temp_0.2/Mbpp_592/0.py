def sum_Of_product(n):
    # Initialize the sum to 0
    sum = 0
    # Iterate from 1 to n
    for i in range(1, n + 1):
        # Calculate the binomial coefficient C(i, j)
        binomial_coefficient = (n - i + 1) // i
        # Multiply the binomial coefficient with the current sum
        sum += binomial_coefficient * i
    return sum