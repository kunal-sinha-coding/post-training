def check_distinct(test_tup):
    # Convert the tuple to a set to remove duplicates
    unique_tup = set(test_tup)
    # Compare the length of the original tuple with the length of the set
    return len(test_tup) == len(unique_tup)