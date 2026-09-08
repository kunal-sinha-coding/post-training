def check_K(tuples, k):
    # Check if the length of the tuples is less than k
    if len(tuples) < k:
        return False
    # Iterate through the tuples and check if the k-th element is present
    for i in range(k):
        if tuples[i] == k:
            return True
    return False