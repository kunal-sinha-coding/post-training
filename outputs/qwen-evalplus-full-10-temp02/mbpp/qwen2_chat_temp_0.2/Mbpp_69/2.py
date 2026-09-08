def is_sublist(main_list, sub_list):
    """
    Check if the main_list contains the sub_list or not.
    
    Parameters:
    main_list (list): The list to search within.
    sub_list (list): The sublist to search for.
    
    Returns:
    bool: True if sub_list is a sublist of main_list, False otherwise.
    """
    # Check if sub_list is empty
    if not sub_list:
        return True
    
    # Iterate through main_list
    for i in range(len(main_list)):
        # Check if the current element matches the first element of sub_list
        if main_list[i] == sub_list[0]:
            # Check if the rest of sub_list matches the rest of main_list starting from the current element
            if sub_list[1:] == main_list[i+1:]:
                return True
    return False