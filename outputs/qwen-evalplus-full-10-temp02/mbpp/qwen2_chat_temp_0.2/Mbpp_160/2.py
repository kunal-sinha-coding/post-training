def find_solution(a, b, n):
    """
    Finds pairs of integers x and y that satisfy the equation ax + by = n.
    
    Parameters:
    a (int): The coefficient of x.
    b (int): The coefficient of y.
    n (int): The constant term.
    
    Returns:
    tuple: A tuple containing the solution (x, y) if it exists, otherwise None.
    """
    # Iterate through possible values of x
    for x in range(-n, n + 1):
        # Calculate the corresponding y value
        y = (n - x * a) / b
        # Check if the calculated y value is an integer
        if y.is_integer():
            return (x, int(y))
    return None