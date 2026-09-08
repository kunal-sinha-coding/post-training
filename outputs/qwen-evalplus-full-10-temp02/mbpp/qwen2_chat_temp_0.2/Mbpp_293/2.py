import math

def otherside_rightangle(a, b):
    # Calculate the hypotenuse using the Pythagorean theorem
    c = math.sqrt(a**2 + b**2)
    # Return the third side of the right triangle
    return c - a
