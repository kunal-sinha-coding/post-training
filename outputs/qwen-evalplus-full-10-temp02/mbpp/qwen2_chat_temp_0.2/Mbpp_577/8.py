def last_Digit_Factorial(n):
    # Initialize the last digit to 1 (since 0! = 1)
    last_digit = 1
    # Loop from n down to 1
    for i in range(n, 0, -1):
        # Multiply the last digit by the current number
        last_digit *= i
    # Return the last digit
    return last_digit
