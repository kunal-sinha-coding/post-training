def merge(list_of_lists):
    # Initialize an empty list to store the merged result
    merged_list = []
    # Iterate over each sublist in the input list
    for sublist in list_of_lists:
        # Extract the first and second elements of the sublist
        first_element = sublist[0]
        second_element = sublist[1]
        # Append the extracted elements to the merged list
        merged_list.append([first_element, second_element])
    # Return the merged list
    return merged_list