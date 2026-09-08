def max_length(list_of_lists):
    # Initialize a variable to store the maximum length found
    max_length = 0
    # Iterate through each sublist in the list
    for sublist in list_of_lists:
        # Check if the current sublist has more elements than the current maximum length
        if len(sublist) > max_length:
            # Update the maximum length if the current sublist has more elements
            max_length = len(sublist)
    # Return the maximum length and the sublist with that length
    return max_length, sublist