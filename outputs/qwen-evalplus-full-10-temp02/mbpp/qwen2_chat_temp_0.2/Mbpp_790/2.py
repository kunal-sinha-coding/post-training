def even_position(lst):
    # Iterate through the list, checking only even indices
    for i in range(0, len(lst), 2):
        # Check if the number at the current even index is even
        if lst[i] % 2 != 0:
            return False
    # If all even indices have even numbers, return True
    return True