def find_lists(tup):
    # Initialize a counter for lists
    count = 0
    # Iterate through each element in the tuple
    for element in tup:
        # Check if the element is a list
        if isinstance(element, list):
            # Increment the counter if it is a list
            count += 1
    # Return the total count of lists
    return count