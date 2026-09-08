def sum_list(a, b):
    """
    Takes two lists [a_1,...,a_n] and [b_1,...,b_n] and returns [a_1+b_1,...,a_n+b_n].
    
    :param a: List of integers
    :param b: List of integers
    :return: List of integers
    """
    # Initialize the result list with the sum of the first elements of both lists
    result = [a[0] + b[0]]
    
    # Iterate through the lists and add the corresponding elements to the result list
    for i in range(1, len(a)):
        result.append(a[i] + b[i])
    
    return result
