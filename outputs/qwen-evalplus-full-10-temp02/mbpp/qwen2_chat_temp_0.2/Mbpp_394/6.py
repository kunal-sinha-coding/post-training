def check_distinct(test_tup):
    # Convert the tuple to a set to remove duplicates
    unique_tup = set(test_tup)
    # Check if the length of the set is the same as the original tuple
    return len(unique_tup) == len(test_tup)