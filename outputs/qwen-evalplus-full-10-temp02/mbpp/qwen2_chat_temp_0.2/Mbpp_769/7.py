def Diff(list1, list2):
    # Calculate the difference between the two lists
    difference = [x for x in list1 if x not in list2]
    return difference