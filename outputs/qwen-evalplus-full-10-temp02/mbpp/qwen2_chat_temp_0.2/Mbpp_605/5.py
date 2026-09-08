def prime_num(n):
    # Check if the number is less than or equal to 1
    if n <= 1:
        return False
    # Check for factors from 2 to the square root of n
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    # If no factors were found, n is prime
    return True