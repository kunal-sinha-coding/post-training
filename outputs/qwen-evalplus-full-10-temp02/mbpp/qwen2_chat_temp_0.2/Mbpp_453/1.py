def sumofFactors(n):
    # Initialize sum of factors to 0
    sum = 0
    # Iterate through possible factors from 1 to n
    for i in range(1, n + 1):
        # Check if i is a factor of n
        if n % i == 0:
            # Add i to the sum if it is even
            sum += i
    # Return the total sum of factors
    return sum