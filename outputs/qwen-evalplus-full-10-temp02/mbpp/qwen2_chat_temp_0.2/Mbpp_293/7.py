import math

def otherside_rightangle(a, b):
    # Calculate the hypotenuse using the Pythagorean theorem
    hypotenuse = math.sqrt(a**2 + b**2)
    # Calculate the third side using the Pythagorean theorem
    third_side = hypotenuse - a - b
    return third_side
