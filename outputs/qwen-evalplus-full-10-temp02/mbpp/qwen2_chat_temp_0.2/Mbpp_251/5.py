def insert_element(lst, element):
    """
    Inserts a given element before each element in the provided list.
    
    Parameters:
    lst (list): The list of elements to be modified.
    element (any): The element to be inserted before each element in the list.
    
    Returns:
    list: A new list with the element inserted before each element in the original list.
    """
    # Initialize an empty list to store the modified list
    modified_list = []
    # Iterate through each element in the original list
    for i in lst:
        # Append the current element to the modified list
        modified_list.append(i)
        # Append the inserted element to the modified list
        modified_list.append(element)
    return modified_list