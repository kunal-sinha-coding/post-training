def first_Digit(number):
    # Check if the number is negative
    if number < 0:
        return -first_Digit(-number)
    # Return the first digit by repeatedly dividing the number by 10
    return number // 10