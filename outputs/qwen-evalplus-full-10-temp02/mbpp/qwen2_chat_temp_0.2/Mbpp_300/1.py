def count_binary_seq(n):
    """
    Calculate the count of all binary sequences of length 2n such that the sum of the first n bits is equal to the sum of the last n bits.
    
    Parameters:
    n (int): The length of the binary sequence.
    
    Returns:
    float: The count of such sequences.
    """
    # Initialize the count of valid sequences
    count = 0
    
    # Iterate over all possible binary sequences of length 2n
    for i in range(2**n):
        # Convert the binary number to a string
        binary_str = bin(i)[2:]
        # Check if the sum of the first n bits is equal to the sum of the last n bits
        if sum(binary_str[:n]) == sum(binary_str[n:]):
            count += 1
    
    return count