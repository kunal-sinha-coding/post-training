def remove_nested(tup):
    # Initialize an empty list to store the result
    result = []
    # Iterate through each element in the input tuple
    for item in tup:
        # Check if the item is a tuple
        if isinstance(item, tuple):
            # Recursively call the function on the nested tuple
            result.extend(remove_nested(item))
        else:
            # If the item is not a tuple, add it to the result list
            result.append(item)
    # Return the list of non-tuple elements
    return result
