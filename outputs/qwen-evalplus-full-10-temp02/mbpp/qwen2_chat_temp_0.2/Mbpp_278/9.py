def count_first_elements(tup):
    # Initialize a counter for the first elements
    count = 0
    # Iterate through the tuple
    for element in tup:
        # Check if the current element is not a tuple
        if not isinstance(element, tuple):
            # Increment the counter if it's not a tuple
            count += 1
    # Return the count of first elements
    return count