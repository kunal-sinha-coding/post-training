def newman_prime(n):
    """
    Find the nth Newman–Shanks–Williams prime number.
    
    Args:
    n (int): The position in the sequence of Newman–Shanks–Williams primes.
    
    Returns:
    int: The nth Newman–Shanks–Williams prime number.
    """
    # Initialize the first two Newman–Shanks–Williams primes
    a, b = 2, 3
    # Generate the sequence of Newman–Shanks–Williams primes
    while True:
        # Calculate the next Newman–Shanks–Williams prime
        c = (a + b) % 1000000007
        a, b = b, c
        # Check if the current prime is a Newman–Shanks–Williams prime
        if is_newman_shanks_williams_prime(c):
            return c

def is_newman_shanks_williams_prime(c):
    """
    Check if a number is a Newman–Shanks–Williams prime.
    
    Args:
    c (int): The number to check.
    
    Returns:
    bool: True if the number is a Newman–Shanks–Williams prime, False otherwise.
    """
    # Check divisibility by 2 and 3
    if c % 2 == 0 or c % 3 == 0:
        return False
    # Check divisibility by 5
    if c % 5 == 0:
        return False
    # Check divisibility by 7
    if c % 7 == 0:
        return False
    # Check divisibility by 11
    if c % 11 == 0:
        return False
    # Check divisibility by 13
    if c % 13 == 0:
        return False
    # Check divisibility by 17
    if c % 17 == 0:
        return False
    # Check divisibility by 19
    if c % 19 == 0:
        return False
    # Check divisibility by 23
    if c % 23 == 0:
        return False
    # Check divisibility by 29
    if c % 29 == 0:
        return False
    # Check divisibility by 31
    if c % 31 == 0:
        return False
    # Check divisibility by 37
    if c % 37 == 0:
        return False
    # Check divisibility by 41
    if c % 41 == 0:
        return False
    # Check divisibility by 43
    if c % 43 == 0:
        return False
    # Check divisibility by 47
    if c % 47 == 0:
        return False
    # Check divisibility by 53
    if c % 53 == 0:
        return False
    # Check divisibility by 59
    if c % 59 == 0:
        return False
    # Check divisibility by 61
    if c % 61 == 0:
        return False
    # Check divisibility by 67
    if c % 67 == 0:
        return False
    # Check divisibility by 71
    if c % 71 == 0:
        return False
    # Check divisibility by 73
    if c % 73 == 0:
        return False
    # Check divisibility by 79
    if c % 79 == 0:
        return False
    # Check divisibility by 83
    if c % 83 == 0:
        return False
    # Check divisibility by 89
    if c % 89 == 0:
        return False
    # Check divisibility by 97
    if c % 97 == 0:
        return False
    # Check divisibility by 101
    if c % 101 == 0:
        return False
    # Check divisibility by 103
    if c % 103 == 0:
        return False
    # Check divisibility by 107
    if c % 107 == 0:
        return False
    # Check divisibility by 109
    if c % 109 == 0:
        return False
    # Check divisibility by 113
    if c % 113 == 0:
        return False
    # Check divisibility by 127
    if c % 127 == 0:
        return False
    # Check divisibility by 131
    if c % 131 == 0:
        return False
    # Check divisibility by 137
    if c % 137 == 0:
        return False
    # Check divisibility by 139
    if c % 139 == 0:
        return False
    # Check divisibility by 149
    if c % 149 == 0:
        return False
    # Check divisibility by 151
    if c % 151 == 0:
        return False
    # Check divisibility by 157
    if c % 157 == 0:
        return False
    # Check divisibility by 163
    if c % 163 == 0:
        return False
    # Check divisibility by 167
    if c % 167 == 0:
        return False
    # Check divisibility by 173
    if c % 173 == 0:
        return False
    # Check divisibility by 179
    if c % 179 == 0:
        return False
    # Check divisibility by 181
    if c % 181 == 0:
        return False
    # Check divisibility by 187
    if c % 187 == 0:
        return False
    # Check divisibility by 191
    if c % 191 == 0:
        return False
    # Check divisibility by 193
    if c % 193 == 0:
        return False
    # Check divisibility by 197
    if c % 197 == 0:
        return False
    # Check divisibility by 201
    if c % 201 == 0:
        return False
    # Check