def tuple_to_dict(tup):
    # Initialize an empty dictionary to store the key-value pairs
    result = {}
    # Iterate over the tuple using a for loop
    for i in range(0, len(tup), 2):
        # Add the key-value pair to the dictionary
        result[tup[i]] = tup[i + 1]
    # Return the dictionary
    return result