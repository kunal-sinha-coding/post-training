def sum_list(a, b):
    """
    This function takes two lists a and b as input and returns their sum.
    
    :param a: List of integers
    :param b: List of integers
    :return: List of integers representing the sum of a and b
    """
    return [a[i] + b[i] for i in range(len(a))]