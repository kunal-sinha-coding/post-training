def even_binomial_Coeff_Sum(n):
    # Initialize the sum of even index binomial coefficients
    sum_even = 0
    
    # Iterate through the first n+1 terms of the binomial coefficients
    for i in range(1, n+1):
        # Calculate the binomial coefficient for the current term
        binomial_coeff = binomial_coefficient(i)
        
        # Check if the index is even
        if i % 2 == 0:
            # Add the even index binomial coefficient to the sum
            sum_even += binomial_coeff
    
    return sum_even