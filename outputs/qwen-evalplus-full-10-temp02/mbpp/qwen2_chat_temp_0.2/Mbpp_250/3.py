def count_X(Tuple, element):
    # Initialize a counter to zero
    count = 0
    # Iterate through each element in the tuple
    for i in Tuple:
        # Check if the current element matches the specified element
        if i == element:
            # Increment the counter if it matches
            count += 1
    # Return the total count of occurrences
    return count