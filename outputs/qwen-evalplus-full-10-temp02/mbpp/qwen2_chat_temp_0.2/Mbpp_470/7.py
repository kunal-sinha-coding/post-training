def add_pairwise(test_tup):
    # Initialize an empty list to store the pairwise additions
    result = []
    # Iterate through the tuple, stopping at the second-to-last element
    for i in range(len(test_tup) - 1):
        # Add the element at index i with the element at index i + 1
        result.append(test_tup[i] + test_tup[i + 1])
    # Return the list of pairwise additions
    return result