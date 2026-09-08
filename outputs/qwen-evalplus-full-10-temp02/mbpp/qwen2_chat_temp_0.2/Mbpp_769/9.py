def Diff(list1, list2):
    # Calculate the difference between the two lists
    diff = [x for x in list1 if x not in list2]
    return diff