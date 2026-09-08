def first_Digit(number):
    # Check if the number is negative
    if number < 0:
        # Convert the number to positive to find the first digit
        number = abs(number)
    # Initialize the first digit as 0
    first_digit = 0
    # Loop through each digit in the number
    while number > 0:
        # Extract the last digit
        last_digit = number % 10
        # Update the first digit
        first_digit = last_digit
        # Remove the last digit from the number
        number //= 10
    return first_digit