def tuple_to_dict(tup):
    # Initialize an empty dictionary to store the key-value pairs
    dict = {}
    # Iterate through the tuple and add each element as a key and its corresponding value to the dictionary
    for i in range(0, len(tup), 2):
        dict[tup[i]] = tup[i + 1]
    # Return the dictionary
    return dict