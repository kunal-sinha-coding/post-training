def max_product(nums):
    # Initialize the maximum product to the first element of the array
    max_product = nums[0]
    # Initialize the minimum product to the first element of the array
    min_product = nums[0]
    # Initialize the result to the first element of the array
    result = nums[0]
    
    # Iterate through the array starting from the second element
    for num in nums[1:]:
        # Update the maximum product if the current number is greater
        if num > max_product:
            max_product = num
        # Update the minimum product if the current number is less
        if num < min_product:
            min_product = num
        # Update the result if the current product is greater
        if num > result:
            result = num
    
    # Return the maximum product found
    return result