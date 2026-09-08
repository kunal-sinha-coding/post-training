import math

def otherside_rightangle(a, b):
    # Calculate the hypotenuse using the Pythagorean theorem
    c = math.sqrt(a**2 + b**2)
    # Calculate the third side using the Pythagorean theorem again
    third_side = c - a - b
    return third_side
