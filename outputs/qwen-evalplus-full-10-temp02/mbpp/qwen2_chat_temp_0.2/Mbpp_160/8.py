def find_solution(a, b, n):
    """
    Finds two integers x and y that satisfy the equation ax + by = n.
    
    Parameters:
    a (int): The coefficient of x.
    b (int): The coefficient of y.
    n (int): The constant term.
    
    Returns:
    tuple: A tuple containing the integers x and y that satisfy the equation, or None if no solution exists.
    """
    # Calculate the discriminant
    discriminant = b**2 - 4*a*n
    
    # Check if the discriminant is non-negative
    if discriminant >= 0:
        # Calculate the two solutions using the quadratic formula
        x = (-b + discriminant**0.5) / (2*a)
        y = (-b - discriminant**0.5) / (2*a)
        return (x, y)
    else:
        return None