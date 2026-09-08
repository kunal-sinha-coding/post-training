def overlapping(seq1, seq2):
    """
    Check if any value in seq1 exists in seq2.
    
    Parameters:
    seq1 (list): The first sequence.
    seq2 (list): The second sequence.
    
    Returns:
    bool: True if any value in seq1 exists in seq2, False otherwise.
    """
    # Iterate through each element in seq1
    for element in seq1:
        # Check if the element is in seq2
        if element in seq2:
            return True
    # If no element from seq1 is found in seq2, return False
    return False