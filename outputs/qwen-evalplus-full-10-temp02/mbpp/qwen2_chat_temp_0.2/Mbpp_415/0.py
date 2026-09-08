def max_Product(arr):
    # Initialize variables to store the maximum product and the minimum product
    max_product = arr[0]
    min_product = arr[0]
    # Initialize the result to store the maximum product found
    result = arr[0]
    
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Update the maximum product if the current element is greater
        if arr[i] > max_product:
            max_product = arr[i]
        # Update the minimum product if the current element is smaller
        if arr[i] < min_product:
            min_product = arr[i]
        # Update the result if the current product is greater than the previously found result
        if arr[i] * max_product > result:
            result = arr[i] * max_product
    
    return result