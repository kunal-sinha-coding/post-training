def find_tuples(tuples_list, k):
    """
    This function takes a list of tuples and a divisor k as input.
    It returns a list of tuples where all elements in the tuples are divisible by k.
    
    :param tuples_list: List of tuples to be filtered.
    :param k: Divisor to check divisibility against.
    :return: List of tuples with all elements divisible by k.
    """
    # Using list comprehension to filter tuples where all elements are divisible by k
    result = [t for t in tuples_list if all(x % k == 0 for x in t)]
    return result
