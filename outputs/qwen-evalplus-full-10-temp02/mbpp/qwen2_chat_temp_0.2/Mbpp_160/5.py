def find_solution(a, b, n):
    """
    Finds integers x and y that satisfy ax + by = n as a tuple.
    If no solution exists, returns None.
    
    Args:
    a (int): The coefficient of x.
    b (int): The coefficient of y.
    n (int): The constant term.
    
    Returns:
    tuple: A tuple (x, y) if a*x + b*y = n, otherwise None.
    """
    # Check if the equation can be solved
    if n % a == 0 and n % b == 0:
        # Calculate the quotient and remainder
        quotient = n // (a * b)
        remainder = n % (a * b)
        
        # Check if the remainder is 0
        if remainder == 0:
            return (quotient, 0)
        else:
            return None
    else:
        return None
