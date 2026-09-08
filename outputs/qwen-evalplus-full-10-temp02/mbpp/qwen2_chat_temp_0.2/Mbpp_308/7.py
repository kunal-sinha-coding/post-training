def large_product(list1, list2, n):
    # Sort the lists in descending order
    list1.sort(reverse=True)
    list2.sort(reverse=True)
    
    # Initialize the result list with the first two elements of the sorted lists
    result = [list1[0], list2[0]]
    
    # Iterate through the sorted lists to find the largest products
    for i in range(1, n):
        # Calculate the product of the current element with the largest product found so far
        current_product = list1[i] * list2[i]
        # Update the result list with the current product
        result.append(current_product)
    
    return result
