# Define the function to replace the last element of the first list with the elements of the second list
def replace_list(list1, list2):
    # Check if the second list is empty
    if not list2:
        # If so, return the first list as is
        return list1
    # Replace the last element of the first list with the elements of the second list
    list1[-1] = list2
    # Return the modified list
    return list1
