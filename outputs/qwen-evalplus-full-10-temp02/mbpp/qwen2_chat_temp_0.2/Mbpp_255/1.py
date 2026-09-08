from itertools import combinations

def combinations_colors(colors, n):
    """
    Generate all combinations (with repetition) of the elements of the list 'colors' and return a list with tuples for each combination.
    
    Parameters:
    colors (list): A list of strings representing colors.
    n (int): The length of the combinations to generate.
    
    Returns:
    list: A list of tuples, each representing a combination of colors.
    """
    return [tuple(combination) for combination in combinations(colors, n)]
