def add_dict_to_tuple(tup, dict1):
    # Convert the dictionary to a tuple
    tuple1 = tuple(dict1.items())
    # Add the tuple to the original tuple
    return tup + tuple1
