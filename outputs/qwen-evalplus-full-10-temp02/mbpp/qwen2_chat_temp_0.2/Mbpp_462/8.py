from itertools import combinations

def combinations_list(lst):
    # Generate all possible combinations of the list
    return list(combinations(lst, len(lst)))
