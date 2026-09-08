def tuple_str_int(tup_str):
    # Convert the string representation of the tuple to a tuple
    return tuple(int(num) for num in tup_str.split(','))
