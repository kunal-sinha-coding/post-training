def merge_sorted_list(list1, list2, list3):
    # Sort the three lists
    sorted_list1 = sorted(list1)
    sorted_list2 = sorted(list2)
    sorted_list3 = sorted(list3)
    
    # Initialize an empty list to store the merged sorted list
    merged_list = []
    
    # Iterate through the sorted lists and append the smallest element to the merged list
    for i in range(min(len(sorted_list1), len(sorted_list2), len(sorted_list3))):
        merged_list.append(sorted_list1[i])
        merged_list.append(sorted_list2[i])
        merged_list.append(sorted_list3[i])
    
    # Return the merged sorted list
    return merged_list