def sum_even_and_even_index(lst):
    # Initialize sum to 0
    sum_even = 0
    # Iterate over the list using index
    for index in range(0, len(lst), 2):  # Start from index 0 and increment by 2 to get even indices
        # Check if the number at the even index is even
        if lst[index] % 2 == 0:
            # Add the even number to the sum
            sum_even += lst[index]
    return sum_even