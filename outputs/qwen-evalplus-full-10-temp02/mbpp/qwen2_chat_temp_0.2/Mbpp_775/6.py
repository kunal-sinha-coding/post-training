def odd_position(lst):
    # Iterate through the list, checking only odd indices
    for i in range(1, len(lst), 2):
        # Check if the number at the current index is odd
        if lst[i] % 2 != 0:
            return False
    # If all odd indices contain odd numbers, return True
    return True