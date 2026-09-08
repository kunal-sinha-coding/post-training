def tuple_to_dict(tup):
    # Initialize an empty dictionary to store the key-value pairs
    result = {}
    # Iterate over the tuple and store each element as a key and its corresponding value
    for i in range(0, len(tup), 2):
        result[tup[i]] = tup[i + 1]
    return result