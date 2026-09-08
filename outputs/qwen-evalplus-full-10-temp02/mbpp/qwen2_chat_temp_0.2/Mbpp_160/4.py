def find_solution(a, b, n):
    """
    Finds integers x and y that satisfy the equation ax + by = n as a tuple.
    Returns None if no solution exists.
    
    Parameters:
    a (int): The coefficient of x.
    b (int): The coefficient of y.
    n (int): The constant term.
    
    Returns:
    tuple: A tuple (x, y) that satisfies the equation ax + by = n, or None if no solution exists.
    """
    # Iterate through possible values of x and y
    for x in range(-100, 101):
        for y in range(-100, 101):
            if a * x + b * y == n:
                return (x, y)
    return None