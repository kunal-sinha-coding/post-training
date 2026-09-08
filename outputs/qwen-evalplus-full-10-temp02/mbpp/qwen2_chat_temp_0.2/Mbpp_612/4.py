def merge(list_of_lists):
    # Initialize an empty list to store the result
    result = []
    # Iterate over each sublist in the input list
    for sublist in list_of_lists:
        # Append the first element of the sublist to the result list
        result.append(sublist[0])
        # Append the second element of the sublist to the result list
        result.append(sublist[1])
    # Return the result list
    return result