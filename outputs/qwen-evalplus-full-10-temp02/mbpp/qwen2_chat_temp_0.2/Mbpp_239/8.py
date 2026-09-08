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
    # Initialize a list to store the number of sequences for each possible length
    sequences = [0] * (n + 1)
    
    # Base case: there's one sequence of length 1
    sequences[1] = 1
    
    # Fill the sequences list
    for i in range(2, n + 1):
        # Each element in the sequence is greater than or equal to twice the previous element
        # and less than or equal to m
        for j in range(2, i + 1):
            # Calculate the number of sequences for the current length
            sequences[i] += sequences[j - 1]
    
    # The total number of sequences is the sum of sequences of length n
    return sequences[n]