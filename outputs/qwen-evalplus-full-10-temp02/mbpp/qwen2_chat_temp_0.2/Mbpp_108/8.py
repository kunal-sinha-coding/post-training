def merge_sorted_list(list1, list2, list3):
    # Combine the three lists into a single list
    merged_list = list1 + list2 + list3
    # Sort the combined list in ascending order
    sorted_list = sorted(merged_list)
    return sorted_list