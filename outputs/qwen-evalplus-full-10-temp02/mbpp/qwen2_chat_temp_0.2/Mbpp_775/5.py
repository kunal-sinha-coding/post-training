def odd_position(lst):
    # Iterate over the list starting from the second element (index 1)
    for i in range(1, len(lst), 2):
        # Check if the current element is odd
        if lst[i] % 2 != 0:
            return False
    # If all odd elements are found, return True
    return True