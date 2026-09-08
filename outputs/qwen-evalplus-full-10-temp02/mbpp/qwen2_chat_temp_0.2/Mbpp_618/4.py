def div_list(list1, list2):
    """
    This function takes two lists as input and returns a new list where each element is the result of dividing the corresponding elements of the input lists.
    
    Parameters:
    list1 (list): The first list.
    list2 (list): The second list.
    
    Returns:
    list: A new list containing the results of element-wise division.
    """
    # Initialize an empty list to store the results
    result = []
    # Iterate over the indices of the two lists
    for i in range(len(list1)):
        # Perform element-wise division and append the result to the result list
        result.append(list1[i] / list2[i])
    # Return the result list
    return result