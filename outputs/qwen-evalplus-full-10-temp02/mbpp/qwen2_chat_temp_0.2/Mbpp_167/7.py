def next_power_of_2(n):
    # Start with the smallest power of 2, which is 1
    power = 1
    # Loop until the power is greater than or equal to n
    while power < n:
        power *= 2
    # Return the power
    return power