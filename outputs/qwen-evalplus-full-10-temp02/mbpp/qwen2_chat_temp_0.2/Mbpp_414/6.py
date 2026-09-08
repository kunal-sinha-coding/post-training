def overlapping(seq1, seq2):
    # Check if there is any common element between seq1 and seq2
    return any(x in seq2 for x in seq1)