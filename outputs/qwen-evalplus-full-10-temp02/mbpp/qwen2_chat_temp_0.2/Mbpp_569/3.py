def sort_sublists(lists):
    # Iterate over each sublist in the list
    for sublist in lists:
        # Sort the sublist of strings
        sublist.sort()
    # Return the modified list of sublists
    return lists