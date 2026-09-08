def pack_consecutive_duplicates(lst):
    # Initialize an empty list to store the result
    result = []
    # Iterate through the list
    for i in range(len(lst) - 1):
        # If the current element is the same as the next element, append the current element to the result
        if lst[i] == lst[i + 1]:
            result.append(lst[i])
        # If the current element is different from the next element, append the current element to the result and start a new sublist
        else:
            result.append(lst[i])
            result.append([])
    # Append the last element of the list to the result if it's not the last element
    if lst[-1] != lst[-2]:
        result.append(lst[-1])
    return result
