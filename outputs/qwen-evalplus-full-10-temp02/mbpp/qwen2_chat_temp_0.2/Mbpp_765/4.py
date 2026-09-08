def is_polite(n):
    """
    This function calculates the nth polite number.
    The nth polite number is defined as the smallest positive integer that is divisible by all integers up to n.
    
    Args:
    n (int): The position of the polite number to find.
    
    Returns:
    int: The nth polite number.
    """
    if n == 1:
        return 1
    count = 0
    num = 1
    while True:
        if all(num % i == 0 for i in range(2, num + 1)):
            count += 1
            if count == n:
                return num
        num += 1