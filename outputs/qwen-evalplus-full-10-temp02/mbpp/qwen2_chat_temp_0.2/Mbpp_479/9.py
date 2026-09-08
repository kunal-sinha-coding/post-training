def first_Digit(number):
    # Check if the number is negative
    if number < 0:
        # Convert the number to positive
        number = -number
    # Extract the first digit by using the modulus operator
    first_digit = number % 10
    return first_digit