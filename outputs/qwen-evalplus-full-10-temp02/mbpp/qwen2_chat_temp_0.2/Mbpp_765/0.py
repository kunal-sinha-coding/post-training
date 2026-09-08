def is_polite(n):
    """
    Find nth polite number.
    geeksforgeeks.org/n-th-polite-number/
    """
    if n == 1:
        return 1
    else:
        count = 0
        num = 1
        while count < n:
            if is_polite(num):
                count += 1
            num += 1
        return num - 1