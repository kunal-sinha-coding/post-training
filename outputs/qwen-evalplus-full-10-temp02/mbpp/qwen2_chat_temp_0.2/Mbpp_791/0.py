def remove_nested(tup):
    # Initialize an empty list to store the non-nested tuples
    non_nested = []
    # Iterate through each element in the input tuple
    for item in tup:
        # Check if the item is not a tuple
        if not isinstance(item, tuple):
            # If it's not a tuple, add it to the non_nested list
            non_nested.append(item)
    # Return the list of non-nested tuples
    return non_nested