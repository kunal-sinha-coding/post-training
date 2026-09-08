def pair_wise(lst):
    # Initialize an empty list to store the pairs
    pairs = []
    # Iterate through the list and check each pair of consecutive items
    for i in range(len(lst) - 1):
        # Append a tuple containing the current item and the next item
        pairs.append((lst[i], lst[i + 1]))
    # Return the list of pairs
    return pairs