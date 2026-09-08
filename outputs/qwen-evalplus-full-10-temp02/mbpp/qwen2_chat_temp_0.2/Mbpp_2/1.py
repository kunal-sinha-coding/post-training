def similar_elements(list1, list2):
    # Convert both lists to sets to remove duplicates and allow for efficient intersection
    set1 = set(list1)
    set2 = set(list2)
    
    # Find the intersection of the two sets
    shared_elements = set1.intersection(set2)
    
    # Convert the set back to a list and return it
    return list(shared_elements)