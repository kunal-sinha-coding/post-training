def sum_div(n):
    # Initialize sum to 0
    sum = 0
    # Iterate through all numbers from 1 to n
    for i in range(1, n + 1):
        # Check if i is a divisor of n
        if n % i == 0:
            # Add i to the sum
            sum += i
    # Return the total sum of divisors
    return sum