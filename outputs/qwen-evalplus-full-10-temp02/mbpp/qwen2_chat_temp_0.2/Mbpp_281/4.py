def all_unique(lst):
    # Convert the list to a set to remove duplicates
    unique_elements = set(lst)
    # Compare the length of the original list with the length of the set
    return len(lst) == len(unique_elements)