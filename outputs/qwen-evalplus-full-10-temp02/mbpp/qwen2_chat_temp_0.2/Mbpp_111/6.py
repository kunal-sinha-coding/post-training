def common_in_nested_lists(nested_list):
    # Initialize an empty set to store common elements
    common_elements = set()
    
    # Iterate through each sublist in the nested list
    for sublist in nested_list:
        # Iterate through each element in the sublist
        for element in sublist:
            # Check if the element is already in the common_elements set
            if element in common_elements:
                continue
            # Add the element to the common_elements set
            common_elements.add(element)
    
    # Return the set of common elements
    return common_elements