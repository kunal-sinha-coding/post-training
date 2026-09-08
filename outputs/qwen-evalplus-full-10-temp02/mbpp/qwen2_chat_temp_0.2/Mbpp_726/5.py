def multiply_elements(t):
    """
    Takes a tuple of numbers (t_1,...,t_{N+1}) and returns a tuple of length N where the i-th element of the tuple is equal to t_i * t_{i+1}.
    
    :param t: Tuple of numbers (t_1,...,t_{N+1})
    :return: Tuple of length N where the i-th element is equal to t_i * t_{i+1}
    """
    return tuple([t[i] * t[i + 1] for i in range(len(t) - 1)])
