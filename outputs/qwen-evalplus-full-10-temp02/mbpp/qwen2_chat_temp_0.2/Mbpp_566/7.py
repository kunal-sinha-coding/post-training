def sum_digits(number):
    # Initialize the sum to 0
    total = 0
    # Loop through each digit in the number
    while number > 0:
        # Add the last digit to the total
        total += number % 10
        # Remove the last digit from the number
        number //= 10
    # Return the total sum of the digits
    return total