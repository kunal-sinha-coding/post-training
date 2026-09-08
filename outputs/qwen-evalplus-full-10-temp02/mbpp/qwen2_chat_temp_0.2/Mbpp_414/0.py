def overlapping(seq1, seq2):
    # Iterate through each element in seq1
    for i in seq1:
        # Check if the current element is also in seq2
        if i in seq2:
            return True
    # If no element from seq1 is found in seq2, return False
    return False