def find_solution(a, b, n):
    """
    Finds two integers x and y that satisfy the equation ax + by = n.
    
    Parameters:
    a (int): The coefficient of x.
    b (int): The coefficient of y.
    n (int): The constant term.
    
    Returns:
    tuple: A tuple containing the solution (x, y) or None if no solution exists.
    """
    # Iterate through possible values of x
    for x in range(-100, 101):
        # Calculate y using the equation ax + by = n
        y = (n - a * x) / b
        # Check if y is an integer
        if y.is_integer():
            return (x, int(y))
    return None