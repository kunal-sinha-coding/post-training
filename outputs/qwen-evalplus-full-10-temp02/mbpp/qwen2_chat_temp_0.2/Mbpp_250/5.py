def count_X(tup, X):
    # Initialize a counter to zero
    count = 0
    # Iterate through each element in the tuple
    for element in tup:
        # Check if the element is equal to the target element
        if element == X:
            # Increment the counter if the element matches the target
            count += 1
    # Return the total count of occurrences
    return count