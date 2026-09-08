def common_element(list1, list2):
    # Convert both lists to sets to remove duplicates and allow for efficient intersection
    set1 = set(list1)
    set2 = set(list2)
    
    # Check if there is any common element between the two sets
    if set1.intersection(set2):
        return True
    else:
        return False