def max_product(nums):
    # Initialize the maximum product to the first element of the array
    max_product = nums[0]
    # Initialize the minimum product to the first element of the array
    min_product = nums[0]
    # Initialize the result to the first element of the array
    result = nums[0]
    
    # Iterate through the array starting from the second element
    for num in nums[1:]:
        # If the current number is greater than the product of the current max and min products
        if num > max_product * min_product:
            # Update the max_product and min_product
            max_product = num
            min_product = num
        # If the current number is less than the product of the current max and min products
        elif num < max_product * min_product:
            # Update the min_product
            min_product = num
        # Otherwise, update the result
        else:
            # Update the result
            result = max(result, num)
    
    # Return the maximum product found
    return result