# Define the function to replace the last element of the first list with the elements of the second list
def replace_list(list1, list2):
    # Check if the lists are of the same length
    if len(list1) != len(list2):
        return "Error: The lists must be of the same length."
    
    # Replace the last element of the first list with the elements of the second list
    list1[-1] = list2
    
    # Return the modified list
    return list1
