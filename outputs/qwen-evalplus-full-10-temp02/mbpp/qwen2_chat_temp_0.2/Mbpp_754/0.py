def extract_index_list(l1, l2, l3):
    # Initialize an empty list to store common elements
    common_elements = []
    # Iterate through each index in the first list
    for index in range(len(l1)):
        # Check if the element at the current index is present in all three lists
        if l1[index] in l2 and l1[index] in l3:
            common_elements.append(l1[index])
    return common_elements