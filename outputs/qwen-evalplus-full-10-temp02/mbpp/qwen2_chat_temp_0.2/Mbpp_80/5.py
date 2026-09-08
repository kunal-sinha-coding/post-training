def tetrahedral_number(n):
    # Base case: the first tetrahedral number is 1
    if n == 1:
        return 1
    # Recursive case: the nth tetrahedral number is n*(n-1)*(n-2)
    else:
        return n * (n-1) * (n-2)