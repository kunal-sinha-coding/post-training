def list_split(lst, n):
    # Initialize an empty list to store the resulting lists
    result = []
    # Iterate over the list in steps of n
    for i in range(0, len(lst), n):
        # Append a sublist of the current range to the result list
        result.append(lst[i:i+n])
    # Return the result list
    return result