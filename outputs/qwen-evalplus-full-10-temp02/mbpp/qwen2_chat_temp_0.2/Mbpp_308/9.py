def large_product(list1, list2, n):
    # Initialize the maximum product to the first element of list1
    max_product = list1[0]
    
    # Iterate through the first list to find the maximum product
    for num in list1:
        if num > max_product:
            max_product = num
    
    # Initialize the second maximum product to the first element of list2
    second_max_product = list2[0]
    
    # Iterate through the second list to find the second maximum product
    for num in list2:
        if num > second_max_product:
            second_max_product = num
    
    # Calculate the product of the two maximum products
    product = max_product * second_max_product
    
    # Return the product
    return product