# Define the function to check for overlapping values
def overlapping(seq1, seq2):
    # Iterate through each element in seq1
    for i in range(len(seq1)):
        # Check if the current element is present in seq2
        if seq1[i] in seq2:
            # Return True if an overlapping value is found
            return True
    # If no overlapping value is found, return False
    return False