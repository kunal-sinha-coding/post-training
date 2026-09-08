def div_list(list1, list2):
    """
    This function takes two lists as input and returns a new list where each element is the division of the corresponding elements in the input lists.
    
    Parameters:
    list1 (list): The first list.
    list2 (list): The second list.
    
    Returns:
    list: A new list containing the division of each corresponding element from list1 and list2.
    """
    # Initialize an empty list to store the results
    result = []
    # Iterate over the indices of the two lists
    for i in range(len(list1)):
        # Calculate the division of the corresponding elements
        result.append(list1[i] / list2[i])
    # Return the list of results
    return result