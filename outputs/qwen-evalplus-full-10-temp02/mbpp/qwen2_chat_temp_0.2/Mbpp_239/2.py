def get_total_number_of_sequences(m, n):
    """
    Calculate the number of possible sequences of length n, where each element is a positive integer
    and is greater than or equal to twice the previous element but less than or equal to m.
    
    Parameters:
    m (int): The upper limit of the range for the elements in the sequence.
    n (int): The length of the sequence.
    
    Returns:
    int: The total number of possible sequences.
    """
    # Initialize the count of sequences
    count = 0
    
    # Iterate through each possible length of the sequence
    for i in range(1, n + 1):
        # Calculate the number of valid sequences of length i
        valid_sequences = m - i + 1
        # Multiply the count by the number of valid sequences for the current length
        count *= valid_sequences
    
    return count