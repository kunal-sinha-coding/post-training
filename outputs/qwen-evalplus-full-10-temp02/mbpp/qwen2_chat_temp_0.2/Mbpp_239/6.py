def get_total_number_of_sequences(m, n):
    """
    This function calculates the number of possible sequences of length n, where each element is a positive integer
    and is greater than or equal to twice the previous element but less than or equal to m.
    
    Parameters:
    m (int): The upper limit of the sequence.
    n (int): The length of the sequence.
    
    Returns:
    int: The total number of possible sequences.
    """
    # Initialize the result to 0
    result = 0
    
    # Iterate through each possible value of the current element
    for i in range(1, n + 1):
        # Calculate the number of valid sequences for the current element
        valid_sequences = (m - i) // 2 + 1
        # Add the number of valid sequences to the result
        result += valid_sequences
    
    return result