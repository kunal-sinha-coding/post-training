def similar_elements(list1, list2):
    # Use set intersection to find common elements between the two lists
    common_elements = set(list1) & set(list2)
    return common_elements