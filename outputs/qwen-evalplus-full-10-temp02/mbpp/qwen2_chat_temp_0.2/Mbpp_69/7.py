def is_sublist(main_list, sub_list):
    """
    Check if the main_list contains the sub_list as a sublist.
    
    Parameters:
    main_list (list): The list to search within.
    sub_list (list): The sublist to search for.
    
    Returns:
    bool: True if sub_list is a sublist of main_list, False otherwise.
    """
    # Check if sub_list is a sublist of main_list
    return sub_list in main_list
