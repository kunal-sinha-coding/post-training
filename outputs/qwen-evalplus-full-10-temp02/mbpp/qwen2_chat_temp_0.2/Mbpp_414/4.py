def overlapping(seq1, seq2):
    """
    Check if any value in seq1 exists in seq2.
    
    Parameters:
    seq1 (list): The first sequence.
    seq2 (list): The second sequence.
    
    Returns:
    bool: True if any value in seq1 exists in seq2, False otherwise.
    """
    for value in seq1:
        if value in seq2:
            return True
    return False