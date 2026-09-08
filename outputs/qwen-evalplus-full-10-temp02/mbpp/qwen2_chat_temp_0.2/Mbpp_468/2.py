def max_product(nums):
    # Initialize the maximum product to the first element of the array
    max_product = nums[0]
    # Initialize the minimum product to the first element of the array
    min_product = nums[0]
    # Initialize the result to the first element of the array
    result = nums[0]
    
    # Iterate through the array starting from the second element
    for num in nums[1:]:
        # If the current number is greater than the maximum product
        if num > max_product:
            # Update the maximum product
            max_product = num
        # If the current number is less than the minimum product
        elif num < min_product:
            # Update the minimum product
            min_product = num
        # If the current number is positive, update the result
        elif num > 0:
            # Update the result by multiplying the current maximum product and the current number
            result = max(result, max_product * num)
        # If the current number is negative, update the result by multiplying the current minimum product and the current number
        else:
            # Update the result by multiplying the current minimum product and the current number
            result = max(result, min_product * num)
    
    # Return the maximum product found
    return result