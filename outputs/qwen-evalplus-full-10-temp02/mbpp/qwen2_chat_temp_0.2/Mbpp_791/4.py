def remove_nested(tup):
    # Initialize an empty list to store the non-nested tuples
    non_nested = []
    # Iterate through each element in the tuple
    for element in tup:
        # Check if the element is not a tuple
        if not isinstance(element, tuple):
            # If it's not a tuple, append it to the non_nested list
            non_nested.append(element)
    # Return the non-nested list
    return non_nested