def common_element(list1, list2):
    # Convert both lists to sets to remove duplicates and allow for efficient lookup
    set1 = set(list1)
    set2 = set(list2)
    
    # Check if there is at least one common element
    if set1.intersection(set2):
        return True
    else:
        return False