def odd_position(lst):
    # Iterate through the list starting from the second element (index 1)
    for i in range(1, len(lst), 2):
        # Check if the current element is odd
        if lst[i] % 2 != 0:
            return False
    # If all elements at odd indices are odd, return True
    return True