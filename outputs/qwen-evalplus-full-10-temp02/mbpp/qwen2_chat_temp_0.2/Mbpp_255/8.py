from itertools import combinations

def combinations_colors(colors, n):
    # Generate all combinations of length n from the list
    return list(combinations(colors, n))