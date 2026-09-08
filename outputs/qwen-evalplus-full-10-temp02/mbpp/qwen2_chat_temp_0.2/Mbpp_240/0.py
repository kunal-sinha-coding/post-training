# Define the function to replace the last element of the first list with the elements of the second list
def replace_list(list1, list2):
    # Check if the length of list1 is greater than or equal to the length of list2
    if len(list1) >= len(list2):
        # Replace the last element of list1 with the elements of list2
        list1[-1] = list2[-1]
    else:
        # If list1 is shorter, append the elements of list2 to the end of list1
        list1.extend(list2)
    return list1
