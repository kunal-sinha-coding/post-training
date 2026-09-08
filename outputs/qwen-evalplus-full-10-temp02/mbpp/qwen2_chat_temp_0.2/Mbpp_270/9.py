def sum_even_and_even_index(lst):
    # Initialize sum to 0
    total_sum = 0
    # Iterate over the list using index
    for index in range(len(lst)):
        # Check if the index is even
        if index % 2 == 0:
            # Check if the number at the even index is even
            if lst[index] % 2 == 0:
                # Add the even number to the total sum
                total_sum += lst[index]
    return total_sum