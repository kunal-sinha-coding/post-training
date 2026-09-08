def sum_Of_Subarray_Prod(arr):
    # Initialize the result variable to store the sum of products
    res = 0
    # Iterate through each element in the array
    for i in range(len(arr)):
        # Initialize the current product to 1
        cur = 1
        # Iterate through each element in the subarray starting from the current element
        for j in range(i, len(arr)):
            # Multiply the current product by the element
            cur *= arr[j]
            # Add the current product to the result
            res += cur
    # Return the result
    return res