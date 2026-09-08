def last_Digit_Factorial(n):
    # Initialize the last digit to 1 (since the factorial of 0 is 1)
    last_digit = 1
    # Loop through each number from 1 to n
    for i in range(1, n + 1):
        # Multiply the last digit by the current number
        last_digit *= i
    # Return the last digit
    return last_digit % 10