def sum_Of_Subarray_Prod(arr):
    # Initialize variables to store the sum of products and the current product
    sum_prod = 1
    current_product = arr[0]
    
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Update the current product by multiplying it with the next element
        current_product *= arr[i]
        
        # Update the sum of products by adding the current product to it
        sum_prod += current_product
    
    # Return the sum of products
    return sum_prod