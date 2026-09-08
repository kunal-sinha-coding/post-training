def power_base_sum(base, power):
    # Initialize the sum to 0
    sum = 0
    # Loop through each digit in the base
    for digit in str(base):
        # Convert the digit back to an integer and add it to the sum
        sum += int(digit)
    # Return the calculated sum
    return sum