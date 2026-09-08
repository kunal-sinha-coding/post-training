import math

def otherside_rightangle(a, b):
    # Calculate the hypotenuse using the Pythagorean theorem
    hypotenuse = math.sqrt(a**2 + b**2)
    # Calculate the third side as the hypotenuse minus the sum of the other two sides
    third_side = hypotenuse - (a + b)
    return third_side