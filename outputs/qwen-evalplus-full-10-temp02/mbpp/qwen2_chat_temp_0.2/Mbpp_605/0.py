def prime_num(num):
    # Check if the number is less than or equal to 1
    if num <= 1:
        return False
    # Check for factors from 2 to the square root of the number
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            return False
    return True