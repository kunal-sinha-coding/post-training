def merge_sorted_list(list1, list2, list3):
    # Sort the input lists
    list1.sort()
    list2.sort()
    list3.sort()
    # Initialize an empty list to store the merged result
    merged_list = []
    # Initialize two pointers for each list
    i, j, k = 0, 0, 0
    # Traverse all elements from both lists
    while i < len(list1) and j < len(list2) and k < len(list3):
        # Compare the elements at the current pointers
        if list1[i] < list2[j] < list3[k]:
            # Add the smaller element to the merged list
            merged_list.append(list1[i])
            i += 1
        elif list1[i] < list3[k]:
            # Add the smaller element to the merged list
            merged_list.append(list1[i])
            i += 1
        else:
            # Add the smaller element to the merged list
            merged_list.append(list3[k])
            k += 1
    # Add remaining elements from the other lists
    merged_list.extend(list1[i:])
    merged_list.extend(list2[j:])
    merged_list.extend(list3[k:])
    return merged_list