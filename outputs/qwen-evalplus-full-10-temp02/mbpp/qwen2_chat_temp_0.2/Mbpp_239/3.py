def get_total_number_of_sequences(m, n):
    """
    Calculate the number of possible sequences of length n, where each element is a positive integer
    and is greater than or equal to twice the previous element but less than or equal to m.
    
    Args:
    m (int): The upper limit of the sequence.
    n (int): The length of the sequence.
    
    Returns:
    int: The total number of possible sequences.
    """
    # Initialize the count of sequences
    count = 0
    
    # Iterate through each possible value of the first element
    for i in range(1, m + 1):
        # Calculate the number of valid sequences for the current element
        valid_sequences = (m - i + 1) // 2
        # Multiply the count by the number of valid sequences for the current element
        count *= valid_sequences
    
    return count