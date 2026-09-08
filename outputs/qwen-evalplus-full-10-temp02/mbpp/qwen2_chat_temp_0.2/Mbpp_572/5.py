def two_unique_nums(lists):
    # Convert each list to a set to remove duplicates
    unique_list = set([num for sublist in lists for num in sublist])
    # Convert the set back to a list and return
    return list(unique_list)