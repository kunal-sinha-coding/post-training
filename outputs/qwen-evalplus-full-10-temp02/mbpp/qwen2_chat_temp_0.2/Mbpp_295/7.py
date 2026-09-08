def sum_div(n):
    # Initialize the sum to 0
    sum = 0
    # Iterate through possible divisors from 1 to n-1
    for i in range(1, n):
        # Check if i is a divisor of n
        if n % i == 0:
            # Add i to the sum
            sum += i
    # Return the total sum of divisors
    return sum