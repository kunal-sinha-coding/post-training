def tuple_to_dict(tup):
    # Initialize an empty dictionary to store the key-value pairs
    dict1 = {}
    # Iterate over the tuple and pair adjacent elements
    for i in range(len(tup) - 1):
        # Add the pair to the dictionary
        dict1[tup[i]] = tup[i + 1]
    # Return the dictionary
    return dict1