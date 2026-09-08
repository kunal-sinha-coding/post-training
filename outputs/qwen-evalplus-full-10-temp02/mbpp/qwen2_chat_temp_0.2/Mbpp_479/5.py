def first_Digit(n):
    # Loop through each digit in the number
    while n >= 10:
        # Remove the last digit
        n //= 10
    # Return the first digit
    return n