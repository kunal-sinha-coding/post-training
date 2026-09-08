def parabola_directrix(a, b, c):
    # Calculate the discriminant of the quadratic equation
    discriminant = b**2 - 4*a*c
    # The directrix of a parabola given by ax^2 + bx + c = 0 is at x = -b / (2a)
    directrix = -b / (2*a)
    return directrix