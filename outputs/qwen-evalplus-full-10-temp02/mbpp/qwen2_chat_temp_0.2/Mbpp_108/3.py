def merge_sorted_list(list1, list2, list3):
    # Sort the input lists
    sorted_list1 = sorted(list1)
    sorted_list2 = sorted(list2)
    sorted_list3 = sorted(list3)
    
    # Initialize an empty list to store the merged sorted list
    merged_list = []
    
    # Iterate through the sorted lists and append elements to the merged list
    for i in range(len(sorted_list1)):
        merged_list.append(sorted_list1[i])
    for i in range(len(sorted_list2)):
        merged_list.append(sorted_list2[i])
    for i in range(len(sorted_list3)):
        merged_list.append(sorted_list3[i])
    
    return merged_list
