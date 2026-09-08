def large_product(list1, list2, n):
    # Sort the lists in descending order
    list1.sort(reverse=True)
    list2.sort(reverse=True)
    
    # Initialize the result list with the first n elements of list1
    result = list1[:n]
    
    # Iterate through the sorted lists and calculate the product of each pair
    for i in range(n):
        for j in range(i + 1, n):
            result.append(list1[i] * list2[j])
    
    return result
