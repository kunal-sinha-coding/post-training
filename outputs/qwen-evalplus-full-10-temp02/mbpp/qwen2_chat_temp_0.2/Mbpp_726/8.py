def multiply_elements(t_1, t_2, t_3, t_4, t_5):
    """
    This function takes a tuple of numbers (t_1,...,t_{N+1}) and returns a tuple of length N where the i-th element of the tuple is equal to t_i * t_{i+1}.
    """
    # Initialize the result tuple with the first element of the input tuple
    result = (t_1, t_2, t_3, t_4, t_5)
    
    # Iterate through the input tuple and multiply each element with the next one
    for i in range(len(t_1)):
        result[i] *= t_2[i + 1]
    
    return result
