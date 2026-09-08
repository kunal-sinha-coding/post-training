def common_in_nested_lists(nested_lists):
    # Initialize an empty set to store common elements
    common_elements = set()
    
    # Iterate through each sublist in the nested lists
    for sublist in nested_lists:
        # Iterate through each element in the sublist
        for element in sublist:
            # Check if the element is already in the common_elements set
            if element in common_elements:
                continue
            # If not, add the element to the common_elements set
            common_elements.add(element)
    
    # Return the set of common elements
    return common_elements