def parabola_directrix(a, b, c):
    # Calculate the discriminant of the quadratic equation
    discriminant = b**2 - 4*a*c
    # Calculate the x-coordinate of the directrix
    x_directrix = -b + discriminant**0.5
    return x_directrix