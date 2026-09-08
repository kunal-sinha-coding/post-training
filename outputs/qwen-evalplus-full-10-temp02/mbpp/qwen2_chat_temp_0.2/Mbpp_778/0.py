def pack_consecutive_duplicates(lst):
    """
    Pack consecutive duplicates of a given list elements into sublists.
    
    Parameters:
    lst (list): The input list of elements.
    
    Returns:
    list: A list of sublists, where each sublist contains consecutive duplicates of the input list elements.
    """
    # Initialize an empty list to store the result
    result = []
    # Iterate through the input list
    for i in range(len(lst) - 1):
        # If the current element is the same as the next element, append the current element to the result
        if lst[i] == lst[i + 1]:
            result.append(lst[i])
        # If the current element is different from the next element, append the result and start a new sublist
        else:
            result.append([lst[i]])
    # Append the last sublist if it's not empty
    if result and result[-1]:
        result.append([lst[-1]])
    return result
