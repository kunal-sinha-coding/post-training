def sort_sublists(lists):
    # Iterate over each sublist in the list
    for sublist in lists:
        # Sort the sublist using the sorted() function
        sublist.sort()
    # Return the modified list of sublists
    return lists
