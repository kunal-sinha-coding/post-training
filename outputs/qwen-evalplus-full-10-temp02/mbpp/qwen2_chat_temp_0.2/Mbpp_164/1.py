def are_equivalent(a, b):
    # Initialize the sum of divisors for both numbers
    sum1 = 0
    sum2 = 0
    
    # Iterate through possible divisors of a
    for i in range(1, a + 1):
        if a % i == 0:
            sum1 += i
    
    # Iterate through possible divisors of b
    for i in range(1, b + 1):
        if b % i == 0:
            sum2 += i
    
    # Check if the sum of divisors of a is equal to the sum of divisors of b
    return sum1 == sum2