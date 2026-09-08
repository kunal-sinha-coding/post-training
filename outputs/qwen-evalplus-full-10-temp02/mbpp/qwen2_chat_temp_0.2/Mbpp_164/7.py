def are_equivalent(a, b):
    # Initialize the sum of divisors for both numbers
    sum_divisors_a = 0
    sum_divisors_b = 0
    
    # Iterate through possible divisors of a
    for i in range(1, a + 1):
        # Check if i is a divisor of a
        if a % i == 0:
            sum_divisors_a += i
    
    # Iterate through possible divisors of b
    for i in range(1, b + 1):
        # Check if i is a divisor of b
        if b % i == 0:
            sum_divisors_b += i
    
    # Check if the sum of divisors of both numbers is the same
    return sum_divisors_a == sum_divisors_b