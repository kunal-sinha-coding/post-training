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
    dp = [0] * (n + 1)
    
    # Base case: there's one sequence of length 1 (the number itself)
    dp[1] = 1
    
    # Fill the dp array
    for i in range(2, n + 1):
        # Each element in the sequence is greater than or equal to twice the previous element
        # and less than or equal to m
        for j in range(2, i + 1):
            # Calculate the number of sequences for the current length
            dp[i] += dp[j - 2]
    
    # The total number of sequences is the sum of all sequences of length n
    return dp[n]
