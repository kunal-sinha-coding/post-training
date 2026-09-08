def catalan_number(n):
    # Base case: if n is 0, return 1
    if n == 0:
        return 1
    # Recursive case: sum of catalan numbers at indices (n-1) and (n-2)
    else:
        return catalan_number(n-1) + catalan_number(n-2)