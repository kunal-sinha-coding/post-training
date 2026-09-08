def prime_num(n):
    # Check if the number is less than or equal to 1
    if n <= 1:
        return False
    # Check if the number is 2
    elif n == 2:
        return True
    # Check for factors from 3 to the square root of n
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True