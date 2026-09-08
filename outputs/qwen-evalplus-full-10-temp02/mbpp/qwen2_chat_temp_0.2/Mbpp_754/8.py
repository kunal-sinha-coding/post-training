def extract_index_list(l1, l2, l3):
    # Initialize an empty list to store common elements
    common_elements = []
    # Iterate through each index of the first list
    for i in range(len(l1)):
        # Check if the element at the current index is present in all three lists
        if l1[i] in l2 and l1[i] in l3:
            # If it is, add it to the common_elements list
            common_elements.append(l1[i])
    # Return the list of common elements
    return common_elements