def max_length(list_of_lists):
    # Initialize a variable to store the maximum length
    max_length = 0
    # Iterate through each sublist in the list
    for sublist in list_of_lists:
        # Check the length of the current sublist
        if len(sublist) > max_length:
            # Update max_length if the current sublist has a greater length
            max_length = len(sublist)
    # Return the maximum length and the corresponding sublist
    return max_length, sublist