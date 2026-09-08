def highest_Power_of_2(n):
    # Initialize the highest power of 2 to 0
    highest_power = 0
    # Loop through the numbers from 1 to n
    for i in range(1, n + 1):
        # Check if the current number is a power of 2
        if i % 2 == 0:
            # Update the highest power if the current number is greater
            highest_power = max(highest_power, i)
    return highest_power