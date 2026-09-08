# Define the function to check if the two integers have opposite signs
def opposite_Signs(x, y):
    # Check if the product of the two numbers is negative
    if x * y < 0:
        return True
    else:
        return False