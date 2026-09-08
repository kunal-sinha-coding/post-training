def count_X(T, X):
    # Initialize a counter to zero
    count = 0
    # Iterate through each element in the tuple
    for i in T:
        # Check if the current element matches the target element
        if i == X:
            # Increment the counter if a match is found
            count += 1
    # Return the total count of occurrences
    return count