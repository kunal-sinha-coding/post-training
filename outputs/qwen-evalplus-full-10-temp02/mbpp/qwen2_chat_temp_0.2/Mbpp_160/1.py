def find_solution(a, b, n):
    """
    Finds integers x and y that satisfy the equation ax + by = n as a tuple.
    If no solution exists, returns None.
    
    :param a: First coefficient of the equation
    :param b: Second coefficient of the equation
    :param n: Constant term of the equation
    :return: A tuple (x, y) if a solution exists, None otherwise
    """
    # Iterate through possible values of x and y
    for x in range(-n, n + 1):
        for y in range(-n, n + 1):
            if a * x + b * y == n:
                return (x, y)
    return None