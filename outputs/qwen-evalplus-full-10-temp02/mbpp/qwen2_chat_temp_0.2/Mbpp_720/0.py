def add_dict_to_tuple(tup, dict):
    # Convert the dictionary to a tuple
    tuple_dict = tuple(dict.items())
    # Add the tuple of dictionary items to the original tuple
    result_tuple = tup + tuple_dict
    return result_tuple