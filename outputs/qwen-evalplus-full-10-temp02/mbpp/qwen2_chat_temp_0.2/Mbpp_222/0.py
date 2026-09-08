def check_type(test_tup):
    # Check if all elements in the tuple have the same data type
    return all(isinstance(x, type(test_tup[0])) for x in test_tup)