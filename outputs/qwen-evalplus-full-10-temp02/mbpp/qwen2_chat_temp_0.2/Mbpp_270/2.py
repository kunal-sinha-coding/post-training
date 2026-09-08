def sum_even_and_even_index(lst):
    # Initialize sum to 0
    sum_even = 0
    # Iterate over the list using index
    for index in range(0, len(lst), 2):
        # Check if the number at the current index is even
        if lst[index] % 2 == 0:
            # Add the even number to the sum
            sum_even += lst[index]
    # Return the final sum
    return sum_even