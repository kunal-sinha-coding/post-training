def even_position(lst):
    # Iterate through the list starting from the second element (index 1)
    for i in range(1, len(lst), 2):
        # Check if the current element is even
        if lst[i] % 2 == 0:
            return False
    # If all even indices contain even numbers, return True
    return True