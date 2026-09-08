def tuple_str_int(tup_str):
    # Convert the string representation of the tuple to a tuple
    return tuple(int(x) for x in tup_str.split(','))