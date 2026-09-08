def add_pairwise(tup):
    # Initialize an empty list to store the pairwise additions
    result = []
    # Iterate through the tuple, starting from the first element
    for i in range(len(tup) - 1):
        # Add the element at index i with the element at index i + 1
        result.append(tup[i] + tup[i + 1])
    # Return the list of pairwise additions
    return result