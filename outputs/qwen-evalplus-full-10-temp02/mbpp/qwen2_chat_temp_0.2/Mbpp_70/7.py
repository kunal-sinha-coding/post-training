def get_equal(tuples_list):
    # Check if all tuples have the same length
    all_equal = all(len(tuple) == len(tup[0]) for tup in tuples_list)
    return all_equal