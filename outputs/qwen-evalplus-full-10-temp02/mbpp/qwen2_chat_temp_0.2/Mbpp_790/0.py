def even_position(lst):
    # Iterate through the list starting from the second element (index 1)
    for i in range(1, len(lst), 2):
        # Check if the current element is even
        if lst[i] % 2 == 0:
            # If it is even, return False
            return False
    # If no even element is found in the even positions, return True
    return True