def count_X(tup, element):
    # Initialize a counter to zero
    count = 0
    # Iterate through each element in the tuple
    for i in tup:
        # Check if the current element matches the target element
        if i == element:
            # Increment the counter if a match is found
            count += 1
    # Return the total count of occurrences
    return count