def add_pairwise(test_tup):
    # Initialize an empty list to store the results
    result = []
    # Iterate through the tuple, starting from the first element
    for i in range(len(test_tup) - 1):
        # Calculate the pairwise addition of the current element and the next element
        result.append(test_tup[i] + test_tup[i + 1])
    # Return the list of results
    return result