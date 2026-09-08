def get_total_number_of_sequences(m, n):
    """
    Calculate the total number of possible sequences of length n, where each element is a positive integer
    and is greater than or equal to twice the previous element but less than or equal to m.
    
    Parameters:
    m (int): The upper limit of the range for the elements in the sequence.
    n (int): The length of the sequence.
    
    Returns:
    int: The total number of sequences.
    """
    # Initialize the result to 0
    result = 0
    
    # Iterate through each possible length of the sequence
    for i in range(1, n + 1):
        # Calculate the number of valid sequences of length i
        valid_sequences = (m - i + 1) // 2
        # Add the number of valid sequences to the result
        result += valid_sequences
    
    return result