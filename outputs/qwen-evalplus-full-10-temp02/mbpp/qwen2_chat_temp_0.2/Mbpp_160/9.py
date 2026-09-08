def find_solution(a, b, n):
    """
    Finds pairs of integers (x, y) that satisfy the equation ax + by = n.
    
    Parameters:
    a (int): The coefficient of x.
    b (int): The coefficient of y.
    n (int): The constant term.
    
    Returns:
    tuple: A tuple containing (x, y) if a solution exists, otherwise None.
    """
    # Iterate through possible values of x
    for x in range(-n, n + 1):
        # Calculate y using the equation ax + by = n
        y = (n - a * x) / b
        # Check if y is an integer
        if y.is_integer():
            return (x, int(y))
    return None
