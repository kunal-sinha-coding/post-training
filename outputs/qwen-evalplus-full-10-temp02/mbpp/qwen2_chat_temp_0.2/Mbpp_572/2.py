def two_unique_nums(lists):
    # Convert each list to a set to remove duplicates
    unique_lists = set([list for sublist in lists for item in sublist])
    # Convert the set back to a list
    return list(unique_lists)