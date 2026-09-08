def merge_sorted_list(list1, list2, list3):
    # Sort the first list
    list1.sort()
    # Sort the second list
    list2.sort()
    # Sort the third list
    list3.sort()
    # Initialize an empty list to store the merged sorted list
    merged_list = []
    # Use two pointers to merge the sorted lists
    i, j, k = 0, 0, 0
    # Continue merging until all elements are merged
    while i < len(list1) and j < len(list2) and k < len(list3):
        if list1[i] < list2[j] < list3[k]:
            merged_list.append(list1[i])
            i += 1
        elif list1[i] < list3[k]:
            merged_list.append(list1[i])
            i += 1
        else:
            merged_list.append(list2[j])
            j += 1
        k += 1
    # Append remaining elements from the sorted lists
    merged_list.extend(list1[i:])
    merged_list.extend(list2[j:])
    merged_list.extend(list3[k:])
    return merged_list
