def add_dict_to_tuple(tup, d):
    # Convert the dictionary to a tuple of tuples
    tuple_of_tuples = tuple(d.items())
    # Concatenate the tuple of tuples with the original tuple
    result = tup + tuple_of_tuples
    return result