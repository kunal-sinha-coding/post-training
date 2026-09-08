def extract_freq(lst):
    # Convert the list to a set to remove duplicates
    unique_tuples = set(lst)
    # Return the length of the set, which represents the number of unique tuples
    return len(unique_tuples)