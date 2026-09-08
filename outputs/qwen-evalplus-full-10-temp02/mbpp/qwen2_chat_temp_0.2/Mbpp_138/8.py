def is_Sum_Of_Powers_Of_Two(n):
    # Initialize a variable to keep track of the sum of powers of 2
    sum_of_powers = 0
    # Loop through each bit position from 0 to 31
    for i in range(32):
        # Check if the current bit is set
        if (n & (1 << i)) != 0:
            # Add the power of 2 to the sum
            sum_of_powers += 2 ** i
    # Check if the sum of powers of 2 equals the original number
    return sum_of_powers == n
