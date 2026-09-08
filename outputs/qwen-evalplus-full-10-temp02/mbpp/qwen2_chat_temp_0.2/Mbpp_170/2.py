def sum_range_list(lst, start, end):
    # Initialize the sum to 0
    total_sum = 0
    # Iterate through the list starting from the start index
    for i in range(start, end + 1):
        # Add the current element to the total sum
        total_sum += lst[i]
    # Return the total sum
    return total_sum