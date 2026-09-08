def sum_Of_Subarray_Prod(nums):
    # Initialize the result variable to store the sum of products
    res = 0
    # Iterate through each element in the list
    for i in range(len(nums)):
        # Initialize the current product to 1
        cur = 1
        # Iterate through each element in the sublist starting from the current index
        for j in range(i, len(nums)):
            # Multiply the current product by the element
            cur *= nums[j]
            # Add the current product to the result
            res += cur
    # Return the result
    return res