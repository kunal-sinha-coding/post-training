def check_type(tup):
    # Check if all elements in the tuple have the same data type
    if all(isinstance(x, type(tup[0])) for x in tup):
        return True
    else:
        return False