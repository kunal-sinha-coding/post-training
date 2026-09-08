def overlapping(seq1, seq2):
    """
    Check if any value in seq1 exists in seq2.
    
    Parameters:
    seq1 (list): The first sequence.
    seq2 (list): The second sequence.
    
    Returns:
    bool: True if any value in seq1 exists in seq2, False otherwise.
    """
    # Iterate through seq2 to check for any element in seq1
    for element in seq2:
        if element in seq1:
            return True
    return False