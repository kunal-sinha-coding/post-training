def get_equal(tuples_list):
    # Check if all tuples have the same length
    if all(len(tuple) == len(tuples_list[0]) for tuple in tuples_list):
        return True
    else:
        return False