def interleave_lists(list1, list2, list3):
    # Initialize an empty list to store the interleaved elements
    interleaved_list = []
    # Iterate through the indices of the three lists
    for i in range(len(list1)):
        # Append the element from list1 to the interleaved list
        interleaved_list.append(list1[i])
        # Append the element from list2 to the interleaved list
        interleaved_list.append(list2[i])
        # Append the element from list3 to the interleaved list
        interleaved_list.append(list3[i])
    # Return the interleaved list
    return interleaved_list