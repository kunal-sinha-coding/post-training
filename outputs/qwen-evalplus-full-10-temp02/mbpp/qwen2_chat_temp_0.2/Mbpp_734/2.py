def sum_Of_Subarray_Prod(nums):
    # Initialize the result variable to store the sum of products
    res = 0
    # Iterate through each element in the list
    for i in range(len(nums)):
        # Initialize the product variable to 1
        prod = 1
        # Iterate through each element in the sublist starting from the current index
        for j in range(i, len(nums)):
            # Multiply the current element with the product
            prod *= nums[j]
            # Add the product to the result
            res += prod
    # Return the result
    return res