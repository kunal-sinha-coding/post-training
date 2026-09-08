def large_product(list1, list2, n):
    # Initialize the maximum product to 0
    max_product = 0
    # Iterate through the first list
    for i in range(n):
        # Calculate the product of the current element with the first list
        product1 = list1[i] * list1[i + 1]
        # Check if the product is greater than the current maximum product
        if product1 > max_product:
            max_product = product1
    # Iterate through the second list
    for j in range(n):
        # Calculate the product of the current element with the second list
        product2 = list2[j] * list2[j + 1]
        # Check if the product is greater than the current maximum product
        if product2 > max_product:
            max_product = product2
    # Return the maximum product found
    return max_product