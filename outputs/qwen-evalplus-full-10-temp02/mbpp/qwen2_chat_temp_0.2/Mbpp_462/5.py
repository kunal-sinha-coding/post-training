def combinations_list(lst):
    # Initialize an empty list to store the combinations
    result = []
    # Use a nested loop to generate all possible combinations
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            # Append the current combination to the result list
            result.append(lst[i:j])
    # Return the list of all combinations
    return result