def Extract(lst):
    # Initialize an empty list to store the first elements of each sublist
    result = []
    # Iterate through each sublist in the input list
    for sublist in lst:
        # Append the first element of the sublist to the result list
        result.append(sublist[0])
    # Return the list of first elements
    return result