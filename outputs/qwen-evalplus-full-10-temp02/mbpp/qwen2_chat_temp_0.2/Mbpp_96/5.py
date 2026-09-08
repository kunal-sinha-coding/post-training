def divisor(n):
    # Initialize the count of divisors
    count = 0
    # Iterate through possible divisors from 1 to n
    for i in range(1, n + 1):
        # Check if i is a divisor of n
        if n % i == 0:
            count += 1
    return count