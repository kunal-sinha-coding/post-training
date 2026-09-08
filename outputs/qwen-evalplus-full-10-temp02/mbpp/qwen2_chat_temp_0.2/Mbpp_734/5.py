def sum_Of_Subarray_Prod(nums):
    # Initialize the result variable to store the sum of products
    result = 0
    # Iterate through each element in the list
    for i in range(len(nums)):
        # Initialize the current product to 1
        current_product = 1
        # Iterate through each element in the sublist starting from the current index
        for j in range(i, len(nums)):
            # Multiply the current product by the element
            current_product *= nums[j]
            # Add the current product to the result
            result += current_product
    # Return the result
    return result