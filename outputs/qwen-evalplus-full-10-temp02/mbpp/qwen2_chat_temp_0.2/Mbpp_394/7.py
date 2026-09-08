def check_distinct(test_tuple):
    # Convert the tuple to a set to remove duplicates
    unique_elements = set(test_tuple)
    # Compare the length of the original tuple with the length of the set
    return len(test_tuple) == len(unique_elements)