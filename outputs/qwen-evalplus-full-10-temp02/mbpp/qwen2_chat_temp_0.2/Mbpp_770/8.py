def odd_num_sum(n):
    # Initialize the sum to 0
    sum_odd = 0
    # Loop through the first n odd natural numbers
    for i in range(1, n + 1, 2):
        # Calculate the fourth power of the current odd number
        fourth_power = i ** 4
        # Add the fourth power to the sum
        sum_odd += fourth_power
    # Return the final sum
    return sum_odd