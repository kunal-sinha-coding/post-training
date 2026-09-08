def max_product(nums):
    # Initialize the maximum product to the first element of the array
    max_product = nums[0]
    # Initialize the minimum product to the first element of the array
    min_product = nums[0]
    # Initialize the result to the first element of the array
    result = nums[0]
    
    # Iterate through the array starting from the second element
    for num in nums[1:]:
        # If the current number is greater than the product of the current max and min
        if num > max_product:
            # Update the max_product to the current number
            max_product = num
        # If the current number is less than the product of the current max and min
        elif num < min_product:
            # Update the min_product to the current number
            min_product = num
        # If the current number is positive, multiply it with the result
        elif num > 0:
            # Update the result to the product of the current max and min
            result = max(result, max_product * num)
        # If the current number is negative, multiply it with the result
        else:
            # Update the result to the product of the current max and min
            result = max(result, min_product * num)
    
    # Return the result
    return result