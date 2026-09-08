def max_product(nums):
    # Initialize variables to store the maximum product and the minimum product
    max_product = nums[0]
    min_product = nums[0]
    result = nums[0]
    
    # Iterate through the array starting from the second element
    for num in nums[1:]:
        # Update the maximum and minimum products
        if num > max_product:
            max_product = num
        if num < min_product:
            min_product = num
        
        # Calculate the maximum product by multiplying max_product and num
        result = max(result, max_product * num)
    
    return result