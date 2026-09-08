def find_tuples(tuples_list, k):
    """
    Find tuples from the given list of tuples where all elements are divisible by k.
    
    Parameters:
    tuples_list (list of tuples): The list of tuples to search through.
    k (int): The divisor to check for divisibility.
    
    Returns:
    list of tuples: A list of tuples containing tuples from tuples_list where all elements are divisible by k.
    """
    # Filter the tuples where all elements are divisible by k
    divisible_tuples = [t for t in tuples_list if all(x % k == 0 for x in t)]
    return divisible_tuples
