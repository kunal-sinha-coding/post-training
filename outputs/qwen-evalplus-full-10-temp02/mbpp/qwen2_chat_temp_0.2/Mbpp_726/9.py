def multiply_elements(t):
    """
    Takes a tuple of numbers (t_1,...,t_{N+1}) and returns a tuple of length N where the i-th element of the tuple is equal to t_i * t_{i+1}.
    
    :param t: Tuple of numbers (t_1,...,t_{N+1})
    :return: Tuple of length N where the i-th element of the tuple is equal to t_i * t_{i+1}
    """
    # Initialize the result tuple with the first element of the input tuple
    result = (t[0],)
    
    # Iterate through the input tuple starting from the second element
    for i in range(1, len(t)):
        # Multiply the current element with the next element and append to the result tuple
        result.append(t[i] * t[i + 1])
    
    return result
