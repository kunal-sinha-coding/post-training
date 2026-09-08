def sort_sublists(list_of_lists):
    # Iterate over each sublist in the list
    for sublist in list_of_lists:
        # Sort the sublist of strings
        sublist.sort()
    # Return the modified list of sublists
    return list_of_lists