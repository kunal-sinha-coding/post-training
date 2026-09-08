def next_power_of_2(n):
    # Initialize the smallest power of 2 to 1
    power = 1
    # Loop until the power is greater than or equal to n
    while power < n:
        power *= 2
    # Return the smallest power of 2 greater than or equal to n
    return power