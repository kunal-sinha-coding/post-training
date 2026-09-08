def count_X(tup, X):
    # Initialize a counter to zero
    count = 0
    # Iterate through each element in the tuple
    for element in tup:
        # Check if the current element is equal to X
        if element == X:
            # Increment the counter if it is
            count += 1
    # Return the total count of occurrences
    return count