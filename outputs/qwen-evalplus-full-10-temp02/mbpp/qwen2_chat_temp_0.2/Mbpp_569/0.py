def sort_sublists(list_of_lists):
    # Iterate through each sublist in the list
    for sublist in list_of_lists:
        # Sort the sublist using the sorted() function
        sublist.sort()
    # Return the modified list of sublists
    return list_of_lists