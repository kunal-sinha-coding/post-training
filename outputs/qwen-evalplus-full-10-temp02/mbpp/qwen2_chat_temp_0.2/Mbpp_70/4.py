def get_equal(tuples_list):
    # Check if all tuples have the same length
    all_equal = all(len(tuple) == len(tuples[0]) for tuple in tuples_list)
    return all_equal