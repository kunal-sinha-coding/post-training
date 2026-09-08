def tuple_str_int(tup_str):
    # Convert the string representation of the tuple to a tuple
    return tuple(int(item) for item in tup_str.split(','))