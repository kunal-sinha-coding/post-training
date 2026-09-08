def max_length(lists):
    # Initialize a variable to store the maximum length
    max_length = 0
    # Iterate through each sublist in the list
    for sublist in lists:
        # Check the length of the current sublist
        if len(sublist) > max_length:
            # Update max_length if the current sublist's length is greater
            max_length = len(sublist)
    # Return the maximum length and the corresponding sublist
    return max_length, sublist