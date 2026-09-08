def Find_Min(lst):
    # Initialize the minimum length to a large number
    min_len = float('inf')
    # Initialize the sublist with the first element of the list
    min_sub = lst[0]
    # Iterate through the list starting from the second element
    for i in range(1, len(lst)):
        # Check if the current sublist is shorter than the minimum length found so far
        if len(lst[i]) < min_len:
            # Update the minimum length and the sublist
            min_len = len(lst[i])
            min_sub = lst[i]
    # Return the sublist with the minimum length
    return min_sub