from itertools import combinations

def combinations_colors(colors, n):
    """
    Generate all combinations of the elements of the list colors with repetition and return a list with a tuple for each combination.
    
    Parameters:
    colors (list): A list of strings representing colors.
    n (int): The length of each combination.
    
    Returns:
    list: A list of tuples, each containing a combination of colors.
    """
    return [tuple(combinations(colors, i)) for i in range(n)]
