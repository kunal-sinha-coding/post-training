def count_X(Tuple, X):
    # Initialize a counter to zero
    count = 0
    # Iterate through each element in the tuple
    for element in Tuple:
        # Check if the element is equal to X
        if element == X:
            # Increment the counter if it is
            count += 1
    # Return the final count
    return count