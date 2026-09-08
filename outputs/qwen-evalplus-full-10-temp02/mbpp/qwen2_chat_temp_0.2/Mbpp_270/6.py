def sum_even_and_even_index(lst):
    # Initialize sum to 0
    total_sum = 0
    # Iterate over the list using index
    for index in range(0, len(lst), 2):
        # Check if the number at the current index is even
        if lst[index] % 2 == 0:
            # Add the even number to the total sum
            total_sum += lst[index]
    # Return the total sum
    return total_sum