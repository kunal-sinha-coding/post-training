def merge(list_of_lists):
    # Initialize an empty list to store the merged result
    merged_list = []
    # Iterate over each sublist in the input list
    for sublist in list_of_lists:
        # Append the first element of the sublist to the merged list
        merged_list.append(sublist[0])
        # Append the second element of the sublist to the merged list
        merged_list.append(sublist[1])
    # Return the merged list
    return merged_list