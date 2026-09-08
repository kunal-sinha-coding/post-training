def combinations_colors(colors, n):
    """
    Generate all combinations (with repetition) of the elements of the list 'colors' and return a list with a tuple for each combination.
    
    :param colors: List of strings representing the colors.
    :param n: Integer representing the length of each combination.
    :return: List of tuples, each containing a combination of 'colors' with length 'n'.
    """
    result = []
    for i in range(1, n + 1):
        for combination in combinations(colors, i):
            result.append(combination)
    return result
