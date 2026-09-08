def div_list(list1, list2):
    """
    This function takes two lists, list1 and list2, and returns a new list where each element is the result of dividing the corresponding elements of list1 by list2.
    
    Parameters:
    list1 (list): The first list.
    list2 (list): The second list.
    
    Returns:
    list: A new list with each element divided by the corresponding element in list2.
    """
    # Initialize an empty list to store the results
    result = []
    # Iterate over the indices of the two lists
    for i in range(len(list1)):
        # Calculate the division of the corresponding elements
        result.append(list1[i] / list2[i])
    # Return the list of results
    return result