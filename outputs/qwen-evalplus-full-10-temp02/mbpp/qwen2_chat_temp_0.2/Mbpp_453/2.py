def sumofFactors(n):
    # Initialize the sum to 0
    sum = 0
    # Iterate through possible factors from 1 to the square root of n
    for i in range(1, int(n**0.5) + 1):
        # Check if i is a factor of n
        if n % i == 0:
            # Add i to the sum
            sum += i
            # Add the corresponding factor if i is not the square root
            if i != n // i:
                sum += n // i
    # Return the total sum of factors
    return sum