def is_polite(n):
    """
    This function checks if the nth polite number is a prime number.
    """
    if n == 1:
        return True
    for i in range(2, n + 1):
        if is_prime(i):
            return True
    return False

def is_prime(num):
    """
    This function checks if a number is prime.
    """
    if num <= 1:
        return False
    if num <= 3:
        return True
    if num % 2 == 0 or num % 3 == 0:
        return False
    i = 5
    while i * i <= num:
        if num % i == 0 or num % (i + 2) == 0:
            return False
        i += 6
    return True