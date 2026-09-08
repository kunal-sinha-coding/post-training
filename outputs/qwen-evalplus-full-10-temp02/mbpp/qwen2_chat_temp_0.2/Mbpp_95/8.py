def Find_Min_Length(lists):
    # Initialize the minimum length to a large number
    min_length = float('inf')
    # Iterate through each sublist in the list
    for sublist in lists:
        # Update the minimum length if the current sublist is smaller
        if len(sublist) < min_length:
            min_length = len(sublist)
    # Return the minimum length found
    return min_length