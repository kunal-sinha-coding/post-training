def interleave_lists(list1, list2, list3):
    # Initialize an empty list to store the interleaved elements
    interleaved_list = []
    # Iterate through the lengths of the three lists
    for i in range(min(len(list1), len(list2), len(list3))):
        # Append elements from the current list to the interleaved list
        interleaved_list.append(list1[i])
        interleaved_list.append(list2[i])
        interleaved_list.append(list3[i])
    return interleaved_list
