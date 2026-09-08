def find_solution(a, b, n):
    """
    Finds integers x and y that satisfy ax + by = n as a tuple, or returns None if no solution exists.
    
    Parameters:
    a (int): The coefficient of x.
    b (int): The coefficient of y.
    n (int): The constant term.
    
    Returns:
    tuple: A tuple (x, y) that satisfies the equation ax + by = n, or None if no solution exists.
    """
    # Check if the equation can be solved
    if n % a == 0 and n % b == 0:
        # Calculate the x and y values
        x = n // a
        y = n // b
        return (x, y)
    else:
        # Return None if no solution exists
        return None