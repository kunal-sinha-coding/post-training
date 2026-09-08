def remove_elements(list1, list2):
    # Use list comprehension to filter out elements present in list2
    return [x for x in list1 if x not in list2]
