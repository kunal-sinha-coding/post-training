def check_type(test_tup):
    # Check if all elements in the tuple are of the same data type
    if all(isinstance(x, type(test_tup[0])) for x in test_tup):
        return True
    else:
        return False