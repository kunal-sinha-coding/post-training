def tuple_str_int(tup_str):
    # Convert the string representation of the tuple to a tuple
    return tuple(map(int, tup_str.split(',')))
