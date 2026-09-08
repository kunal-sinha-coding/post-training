def large_product(list1, list2, n):
    # Initialize the maximum product to 0
    max_product = 0
    # Iterate through the first list
    for i in range(n):
        # Multiply the current element with the maximum product found so far
        max_product = max(max_product, list1[i] * list2[i])
    # Return the maximum product found
    return max_product