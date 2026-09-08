def last_Digit_Factorial(n):
    # Initialize the last digit to 1 (since 0! = 1)
    last_digit = 1
    # Loop through each digit in the factorial
    for i in range(1, n + 1):
        # Multiply the last digit by the current digit
        last_digit *= i
    # Return the last digit
    return last_digit % 10