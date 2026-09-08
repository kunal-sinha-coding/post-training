def add_pairwise(test_tup):
    # Initialize an empty list to store the results
    result = []
    # Iterate through the tuple, stopping one element before the end
    for i in range(len(test_tup) - 1):
        # Add the sum of the current element and the next element to the result list
        result.append(test_tup[i] + test_tup[i + 1])
    # Return the list of results
    return result