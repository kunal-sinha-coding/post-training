def multiply_elements(t_1, t_2, t_3, t_4, t_5):
    """
    This function takes a tuple of numbers (t_1,...,t_{N+1}) and returns a tuple of length N where the i-th element of the tuple is equal to t_i * t_{i+1}.
    
    :param t_1: First element of the tuple
    :param t_2: Second element of the tuple
    :param t_3: Third element of the tuple
    :param t_4: Fourth element of the tuple
    :param t_5: Fifth element of the tuple
    :return: A tuple of length N where the i-th element is equal to t_i * t_{i+1}
    """
    return (t_1 * t_2, t_2 * t_3, t_3 * t_4, t_4 * t_5)
