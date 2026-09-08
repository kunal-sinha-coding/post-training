def check_type(tup):
    # Check if all elements in the tuple are of the same data type
    return all(isinstance(x, type(tup[0])) for x in tup)