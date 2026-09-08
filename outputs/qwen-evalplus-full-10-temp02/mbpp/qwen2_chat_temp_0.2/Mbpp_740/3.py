def tuple_to_dict(tup):
    # Initialize an empty dictionary to store the key-value pairs
    result_dict = {}
    # Iterate over the tuple using a for loop
    for i in range(0, len(tup), 2):
        # Extract the key and value from the tuple
        key = tup[i]
        value = tup[i + 1]
        # Add the key-value pair to the dictionary
        result_dict[key] = value
    # Return the resulting dictionary
    return result_dict