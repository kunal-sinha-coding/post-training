def consecutive_duplicates(lst):
    # Initialize an empty list to store the result
    result = []
    # Iterate through the list
    for i in range(len(lst)):
        # If the current element is not the same as the previous one
        if lst[i] != lst[i - 1]:
            # Append the current element to the result list
            result.append(lst[i])
    # Return the result list
    return result