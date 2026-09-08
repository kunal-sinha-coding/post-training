def count_Primes_nums(n):
    # Initialize a counter for prime numbers
    count = 0
    # Iterate through all numbers from 2 to n-1
    for i in range(2, n):
        # Check if the number is prime
        if is_prime(i):
            count += 1
    return count

def is_prime(num):
    # Check if the number is less than 2
    if num < 2:
        return False
    # Check for factors from 2 to the square root of the number
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            return False
    return True