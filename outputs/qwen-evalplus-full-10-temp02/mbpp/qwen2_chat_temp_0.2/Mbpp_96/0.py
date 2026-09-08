def divisor(n):
    # Initialize the count of divisors to 0
    count = 0
    # Iterate through all numbers from 1 to n-1
    for i in range(1, n):
        # Check if i is a divisor of n
        if n % i == 0:
            # Increment the count if i is a divisor
            count += 1
    # Return the count of divisors
    return count