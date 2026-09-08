def even_binomial_Coeff_Sum(n):
    # Initialize the sum of even index binomial coefficients
    sum_even = 0
    
    # Iterate through the range from 0 to n-1
    for i in range(n):
        # Check if the index is even
        if i % 2 == 0:
            # Calculate the binomial coefficient for the current index
            binomial_coeff = binomial_coefficient(i, n)
            # Add the binomial coefficient to the sum
            sum_even += binomial_coeff
    
    return sum_even
