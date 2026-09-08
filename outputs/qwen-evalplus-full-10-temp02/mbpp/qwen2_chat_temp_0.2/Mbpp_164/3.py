def are_equivalent(a, b):
    # Initialize the sum of divisors for both numbers
    sum_a = 0
    sum_b = 0
    
    # Iterate through possible divisors of a
    for i in range(1, a + 1):
        if a % i == 0:
            sum_a += i
    
    # Iterate through possible divisors of b
    for i in range(1, b + 1):
        if b % i == 0:
            sum_b += i
    
    # Check if the sum of divisors of both numbers is the same
    return sum_a == sum_b