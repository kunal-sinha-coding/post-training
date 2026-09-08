def large_product(list1, list2, n):
    # Initialize the maximum product to a very small number
    max_product = float('-inf')
    
    # Iterate through each pair of factors
    for i in range(n):
        for j in range(n):
            # Calculate the product of the two factors
            product = list1[i] * list2[j]
            # Update the maximum product if the current product is greater
            if product > max_product:
                max_product = product
    
    # Return the list of the maximum products
    return [max_product]