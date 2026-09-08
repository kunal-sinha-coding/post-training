def sum_of_common_divisors(x, y):
    # Initialize the sum of common divisors to 0
    sum_common = 0
    # Iterate through possible divisors from 1 to the minimum of x and y
    for i in range(1, min(x, y) + 1):
        # Check if i is a divisor of both x and y
        if x % i == 0 and y % i == 0:
            # Add i to the sum of common divisors
            sum_common += i
    # Return the total sum of common divisors
    return sum_common