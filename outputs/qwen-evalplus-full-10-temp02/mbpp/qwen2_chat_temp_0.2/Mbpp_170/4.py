def sum_range_list(numbers, start, end):
    # Initialize the sum to 0
    total_sum = 0
    # Loop through the list from start to end
    for i in range(start, end + 1):
        # Add the current number to the total sum
        total_sum += numbers[i]
    # Return the total sum
    return total_sum