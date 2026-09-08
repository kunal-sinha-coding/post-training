def similar_elements(list1, list2):
    # Use set intersection to find common elements
    common_elements = list(set(list1) & set(list2))
    return common_elements