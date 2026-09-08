def get_equal(tuples):
    # Check if all tuples have the same length
    return all(len(tuple) == len(tup) for tup in tuples)