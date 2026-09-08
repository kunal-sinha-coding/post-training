def add_pairwise(tup):
    # Initialize an empty list to store the pairwise sums
    pairwise_sums = []
    # Iterate through the tuple, stopping at the second-to-last element
    for i in range(len(tup) - 1):
        # Calculate the pairwise sum of the current element and the next element
        pairwise_sum = tup[i] + tup[i + 1]
        # Append the pairwise sum to the list
        pairwise_sums.append(pairwise_sum)
    # Return the list of pairwise sums
    return pairwise_sums