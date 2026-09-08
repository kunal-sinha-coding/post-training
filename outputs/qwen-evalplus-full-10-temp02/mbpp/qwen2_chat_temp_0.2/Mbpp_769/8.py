def Diff(list1, list2):
    # Calculate the difference between the two lists
    result = [x for x in list1 if x not in list2]
    return result