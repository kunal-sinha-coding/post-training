def parabola_directrix(a, b, c):
    """
    Find the directrix of a parabola given its coefficients a, b, and c.
    
    Parameters:
    a (int): The coefficient of x^2.
    b (int): The coefficient of x.
    c (int): The constant term.
    
    Returns:
    int: The directrix of the parabola.
    """
    # Calculate the discriminant
    discriminant = b**2 - 4*a*c
    
    # Calculate the directrix
    directrix = -b + discriminant**0.5
    
    return directrix