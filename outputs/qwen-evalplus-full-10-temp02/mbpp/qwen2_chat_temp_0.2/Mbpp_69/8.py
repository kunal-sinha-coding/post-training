def is_sublist(main_list, sub_list):
    """
    Check if the main_list contains the sub_list as a sublist.
    
    Parameters:
    main_list (list): The list to search within.
    sub_list (list): The sublist to search for.
    
    Returns:
    bool: True if sub_list is a sublist of main_list, False otherwise.
    """
    # Check if sub_list is empty
    if not sub_list:
        return True
    
    # Check if sub_list is a sublist of main_list
    return any(main_list[i:i+len(sub_list)] == sub_list for i in range(len(main_list) - len(sub_list) + 1))
