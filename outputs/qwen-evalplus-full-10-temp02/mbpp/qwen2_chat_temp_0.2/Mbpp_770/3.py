def odd_num_sum(n):
    # Initialize the sum to 0
    total_sum = 0
    # Loop through the first n odd natural numbers
    for i in range(1, 2*n, 2):
        # Calculate the fourth power of the current odd number
        fourth_power = i**4
        # Add the fourth power to the total sum
        total_sum += fourth_power
    # Return the total sum
    return total_sum