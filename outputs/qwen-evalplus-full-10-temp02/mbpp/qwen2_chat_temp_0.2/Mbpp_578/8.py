def interleave_lists(list1, list2, list3):
    # Initialize an empty list to store the interleaved elements
    interleaved_list = []
    # Iterate through the lengths of the input lists
    for i in range(len(list1)):
        # Append elements from list1 to interleaved_list
        interleaved_list.append(list1[i])
        # Append elements from list2 to interleaved_list
        interleaved_list.append(list2[i])
        # Append elements from list3 to interleaved_list
        interleaved_list.append(list3[i])
    # Return the interleaved list
    return interleaved_list
