def Extract(lst):
    # Initialize an empty list to store the first elements of each sublist
    first_elements = []
    # Iterate over each sublist in the input list
    for sublist in lst:
        # Append the first element of the current sublist to the first_elements list
        first_elements.append(sublist[0])
    # Return the list of first elements
    return first_elements