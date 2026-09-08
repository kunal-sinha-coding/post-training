def sum_in_range(l, r):
    # Initialize the sum to 0
    total_sum = 0
    # Iterate through each number in the range
    for num in range(l, r + 1):
        # Check if the number is odd
        if num % 2 != 0:
            # Add the odd number to the total sum
            total_sum += num
    # Return the total sum
    return total_sum