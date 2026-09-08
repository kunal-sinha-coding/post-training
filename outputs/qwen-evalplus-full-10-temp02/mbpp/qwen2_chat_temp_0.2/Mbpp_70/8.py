def get_equal(tuples):
    # Check if all tuples have the same length
    return all(len(tuple) == len(tup[0]) for tup in tuples)