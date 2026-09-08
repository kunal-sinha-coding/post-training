def large_product(list1, list2, n):
    # Sort the lists in descending order
    list1.sort(reverse=True)
    list2.sort(reverse=True)
    
    # Initialize the result list with the first two elements of the sorted lists
    result = [list1[0], list2[0]]
    
    # Iterate through the sorted lists to find the largest products
    for i in range(1, n):
        # Calculate the product of the current element from list1 and the current element from list2
        product = list1[i] * list2[i]
        # Append the product to the result list
        result.append(product)
    
    return result