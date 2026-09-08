def power_base_sum(base, power):
    # Initialize the sum of digits to 0
    sum_digits = 0
    
    # Loop through each digit in the base
    for digit in str(base):
        # Convert the digit back to an integer and add it to the sum
        sum_digits += int(digit)
    
    # Calculate the sum of the digits raised to the power
    result = sum_digits ** power
    
    return result