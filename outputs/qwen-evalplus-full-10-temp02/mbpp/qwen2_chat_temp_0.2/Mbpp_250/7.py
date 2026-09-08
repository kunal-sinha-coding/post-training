def count_X(Tuple, X):
    # Initialize a counter to zero
    count = 0
    # Iterate through each element in the tuple
    for element in Tuple:
        # Check if the current element matches the target element
        if element == X:
            # Increment the counter if it matches
            count += 1
    # Return the total count of occurrences
    return count