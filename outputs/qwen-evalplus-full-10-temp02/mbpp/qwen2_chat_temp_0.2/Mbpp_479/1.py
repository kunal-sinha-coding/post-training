def first_Digit(number):
    # Check if the number is negative
    if number < 0:
        number = -number  # Make the number positive
    # Extract the first digit by repeatedly dividing the number by 10
    while number >= 10:
        number //= 10
    return number