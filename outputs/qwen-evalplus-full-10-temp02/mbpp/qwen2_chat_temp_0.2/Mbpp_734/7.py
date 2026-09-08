def sum_Of_Subarray_Prod(arr):
    # Initialize the result variable to store the sum of products
    result = 0
    # Iterate through each element in the array
    for i in range(len(arr)):
        # Initialize the product variable to store the current product of subarray
        product = 1
        # Iterate through each element in the current subarray
        for j in range(i, len(arr)):
            # Multiply the current product by the element
            product *= arr[j]
            # Add the product to the result
            result += product
    # Return the result
    return result