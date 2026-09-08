def power_base_sum(base, power):
    # Initialize the sum to 0
    sum = 0
    # Loop through each digit in the base
    for digit in str(base):
        # Convert the digit back to an integer
        digit = int(digit)
        # Add the digit to the sum
        sum += digit
    # Return the final sum
    return sum