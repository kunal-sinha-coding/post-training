def even_position(lst):
    # Iterate through the list using index
    for i in range(len(lst)):
        # Check if the index is even
        if i % 2 == 0:
            # Check if the number at the current index is even
            if lst[i] % 2 == 0:
                return False
    # If no even index contains even numbers, return True
    return True