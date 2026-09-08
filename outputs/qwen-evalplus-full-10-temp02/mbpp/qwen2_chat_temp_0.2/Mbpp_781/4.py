def count_divisors(n):
    # Initialize the count of divisors to 0
    count = 0
    # Iterate through possible divisors from 1 to n-1
    for i in range(1, n):
        # If i is a divisor of n, increment the count
        if n % i == 0:
            count += 1
    # Return the count of divisors
    return count