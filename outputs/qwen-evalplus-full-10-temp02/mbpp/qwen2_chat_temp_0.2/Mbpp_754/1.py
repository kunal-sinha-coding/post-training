def extract_index_list(l1, l2, l3):
    # Initialize an empty list to store common elements
    common_elements = []
    # Iterate through each element in the first list
    for element in l1:
        # Check if the element is present in all three lists
        if element in l2 and element in l3:
            # If it is, add it to the common_elements list
            common_elements.append(element)
    # Return the list of common elements
    return common_elements