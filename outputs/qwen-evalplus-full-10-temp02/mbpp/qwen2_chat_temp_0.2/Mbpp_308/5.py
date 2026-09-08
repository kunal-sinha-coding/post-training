def large_product(list1, list2, n):
    # Initialize variables to store the maximum product and the indices of the factors
    max_product = float('-inf')
    max_indices = [-1, -1]
    
    # Iterate through the first list to find the maximum product
    for i in range(n):
        if list1[i] > max_product:
            max_product = list1[i]
            max_indices = [i, 0]
    
    # Iterate through the second list to find the maximum product
    for i in range(n):
        if list2[i] > max_product:
            max_product = list2[i]
            max_indices = [0, i]
    
    # Calculate the product of the factors from both lists
    product1 = list1[max_indices[0]] * list1[max_indices[1]]
    product2 = list2[max_indices[0]] * list2[max_indices[1]]
    
    # Return the product of the two factors
    return [product1, product2]