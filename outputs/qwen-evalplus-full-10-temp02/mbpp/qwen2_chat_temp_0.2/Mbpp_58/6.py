# Define the function to check if the two integers have opposite signs
def opposite_Signs(num1, num2):
    # Check if the product of the two numbers is negative
    if num1 * num2 < 0:
        return True
    else:
        return False