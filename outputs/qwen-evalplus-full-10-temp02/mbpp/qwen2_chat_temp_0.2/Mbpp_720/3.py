def add_dict_to_tuple(tup, dict1):
    # Convert the dictionary to a tuple of key-value pairs
    tuple1 = tuple(dict1.items())
    # Add the tuple of key-value pairs to the original tuple
    result = tup + tuple1
    return result