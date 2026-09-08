def are_equivalent(a, b):
    # Calculate the sum of the divisors of both numbers
    sum_divisors_a = sum(divisor for divisor in range(1, a + 1) if a % divisor == 0)
    sum_divisors_b = sum(divisor for divisor in range(1, b + 1) if b % divisor == 0)
    
    # Check if the sum of the divisors of both numbers is the same
    return sum_divisors_a == sum_divisors_b