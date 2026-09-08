def pack_consecutive_duplicates(lst):
    # Initialize an empty list to store the result
    result = []
    # Iterate through the list
    for i in range(len(lst) - 1):
        # If the current element is the same as the next element, append it to the result
        if lst[i] == lst[i + 1]:
            result.append([lst[i]])
        else:
            # Otherwise, append the current element to the result list and start a new sublist
            result.append([lst[i]])
    # Append the last element to the result list if it's not the last element in the list
    if lst[-1] != lst[-2]:
        result.append([lst[-1]])
    return result
