def large_product(list1, list2, n):
    # Initialize variables to store the maximum product and the indices of the largest factors
    max_product = float('-inf')
    max_index1 = -1
    max_index2 = -1
    
    # Iterate through the first list to find the largest factor
    for i in range(len(list1)):
        if list1[i] > max_product:
            max_product = list1[i]
            max_index1 = i
    
    # Iterate through the second list to find the largest factor
    for i in range(len(list2)):
        if list2[i] > max_product:
            max_product = list2[i]
            max_index2 = i
    
    # If both indices are negative, return None as there are no positive factors
    if max_index1 < 0 or max_index2 < 0:
        return None
    
    # Calculate the product of the two largest factors
    product = list1[max_index1] * list2[max_index2]
    
    # Return the product and the indices of the largest factors
    return [product, max_index1, max_index2]
