def sum_in_range(l, r):
    # Initialize sum to 0
    sum = 0
    # Loop through the range from l to r
    for i in range(l, r + 1):
        # Check if the number is odd
        if i % 2 != 0:
            # Add the odd number to the sum
            sum += i
    # Return the total sum of odd numbers
    return sum