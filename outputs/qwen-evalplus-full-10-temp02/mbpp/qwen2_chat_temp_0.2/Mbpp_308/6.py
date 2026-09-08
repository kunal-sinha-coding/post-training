def large_product(list1, list2, n):
    # Sort the lists in descending order
    list1.sort(reverse=True)
    list2.sort(reverse=True)
    
    # Initialize the result list with the first n elements of the sorted lists
    result = list1[:n]
    
    # Iterate through the sorted lists to find the largest product
    for i in range(n):
        for j in range(i + 1, n):
            # Calculate the product of the two elements
            product = list1[i] * list2[j]
            # Append the product to the result list
            result.append(product)
    
    return result