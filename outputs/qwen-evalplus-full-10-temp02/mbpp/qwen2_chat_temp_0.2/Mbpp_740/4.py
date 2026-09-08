def tuple_to_dict(input_tuple):
    # Initialize an empty dictionary to store the key-value pairs
    result_dict = {}
    # Iterate over the input tuple
    for i in range(0, len(input_tuple), 2):
        # Extract the key and value from the tuple
        key = input_tuple[i]
        value = input_tuple[i + 1]
        # Add the key-value pair to the dictionary
        result_dict[key] = value
    # Return the dictionary
    return result_dict