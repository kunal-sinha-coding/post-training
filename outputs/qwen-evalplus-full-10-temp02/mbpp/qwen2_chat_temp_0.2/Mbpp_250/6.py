def count_X(tup, x):
    # Initialize a counter to zero
    count = 0
    # Iterate through each element in the tuple
    for i in tup:
        # Check if the current element is equal to the target element
        if i == x:
            # Increment the counter if it is
            count += 1
    # Return the total count of occurrences
    return count