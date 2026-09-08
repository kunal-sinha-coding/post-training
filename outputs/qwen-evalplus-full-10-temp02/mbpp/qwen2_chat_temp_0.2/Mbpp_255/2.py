def combinations_colors(colors, n):
    """
    Generate all combinations (with repetition) of the elements of the list 'colors' and return a list with a tuple for each combination.
    
    :param colors: List of strings
    :param n: Integer representing the length of each combination
    :return: List of tuples, each tuple representing a combination of 'colors'
    """
    # Initialize an empty list to store the combinations
    combinations = []
    # Iterate over the range of possible combinations of length 'n'
    for i in range(1, n + 1):
        # Generate all combinations of length 'i' from the list 'colors'
        for combination in combinations_of_length(colors, i):
            # Append the combination as a tuple to the list of combinations
            combinations.append(combination)
    return combinations
