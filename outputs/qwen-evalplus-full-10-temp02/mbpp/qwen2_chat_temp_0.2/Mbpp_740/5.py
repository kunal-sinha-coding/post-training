def tuple_to_dict(tup):
    # Initialize an empty dictionary to store the key-value pairs
    dict1 = {}
    # Iterate through the tuple using a for loop
    for i in range(0, len(tup), 2):
        # Add the current element as the key and the next element as the value to the dictionary
        dict1[tup[i]] = tup[i + 1]
    # Return the dictionary
    return dict1