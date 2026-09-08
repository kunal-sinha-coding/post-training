def pack_consecutive_duplicates(lst):
    # Initialize an empty list to store the result
    result = []
    # Iterate through the list
    for i in range(len(lst) - 1):
        # If the current element is the same as the next element, append the current element to the result list
        if lst[i] == lst[i + 1]:
            result.append(lst[i])
        else:
            # If the current element is different from the next element, append the result list and start a new one
            result.append([lst[i]])
    # Append the last sublist if it's not empty
    if result:
        result.append([lst[-1]])
    return result