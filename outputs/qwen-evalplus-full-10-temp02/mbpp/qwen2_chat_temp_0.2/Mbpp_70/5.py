def get_equal(tuples_list):
    # Check if all tuples have the same length
    all_same_length = all(len(tup) == len(tup_list[0]) for tup in tuples_list)
    return all_same_length