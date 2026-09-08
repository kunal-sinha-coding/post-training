def remove_elements(list1, list2):
    # Use list comprehension to filter out elements present in list2
    return [item for item in list1 if item not in list2]