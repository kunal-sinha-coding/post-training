def combinations_list(lst):
    # Initialize an empty list to store the combinations
    result = []
    # Iterate over each element in the input list
    for i in range(len(lst)):
        # Iterate over each possible combination of elements starting from the current element
        for j in range(i + 1, len(lst)):
            # Append the current combination to the result list
            result.append(lst[i:j])
    # Return the list of all combinations
    return result