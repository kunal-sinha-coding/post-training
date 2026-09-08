def sum_range_list(numbers, start, end):
    # Initialize the sum to 0
    total_sum = 0
    # Iterate through the list starting from the start index
    for i in range(start, end + 1):
        # Add the current number to the total sum
        total_sum += numbers[i]
    # Return the total sum
    return total_sum