def highest_Power_of_2(n):
    # Initialize the highest power of 2 to 0
    highest_power = 0
    # Loop through all numbers from 1 to n
    for i in range(1, n + 1):
        # Check if the current number is a power of 2
        if i & (i - 1) == 0:
            # If it is, update the highest power
            highest_power = i
    return highest_power