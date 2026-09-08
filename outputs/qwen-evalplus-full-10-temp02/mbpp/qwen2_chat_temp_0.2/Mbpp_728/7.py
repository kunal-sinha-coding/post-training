def sum_list(a, b):
    """
    Takes two lists [a_1,...,a_n] and [b_1,...,b_n] and returns [a_1+b_1,...,a_n+b_n].
    """
    return [a[i] + b[i] for i in range(len(a))]