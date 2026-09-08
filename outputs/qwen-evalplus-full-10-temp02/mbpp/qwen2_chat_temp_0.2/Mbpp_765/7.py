def is_polite(n):
    """
    This function checks if the nth polite number is a prime number.
    """
    if n <= 0:
        return False
    if n == 1:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True