def get_total_number_of_sequences(m, n):
    """
    Calculate the number of possible sequences of length n, where each element is a positive integer
    and is greater than or equal to twice the previous element but less than or equal to m.
    
    Parameters:
    m (int): The upper limit of the sequence.
    n (int): The length of the sequence.
    
    Returns:
    int: The total number of possible sequences.
    """
    # Initialize the result to 0
    result = 0
    
    # Iterate through each possible length of the sequence
    for i in range(1, n + 1):
        # Calculate the number of sequences of length i
        # This is the sum of sequences of length i-1 and i-2
        result += get_total_number_of_sequences(m, i - 1) + get_total_number_of_sequences(m, i - 2)
    
    return result