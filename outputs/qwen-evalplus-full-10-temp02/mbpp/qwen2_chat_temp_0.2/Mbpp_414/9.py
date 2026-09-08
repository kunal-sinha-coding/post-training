def overlapping(sequence1, sequence2):
    """
    Check if any value in sequence1 exists in sequence2.
    
    Args:
    sequence1 (list): The first sequence to check.
    sequence2 (list): The second sequence to check for overlaps.
    
    Returns:
    bool: True if any value in sequence1 exists in sequence2, False otherwise.
    """
    # Iterate through each element in sequence1
    for element in sequence1:
        # Check if the element is in sequence2
        if element in sequence2:
            return True
    # If no element from sequence1 is found in sequence2, return False
    return False