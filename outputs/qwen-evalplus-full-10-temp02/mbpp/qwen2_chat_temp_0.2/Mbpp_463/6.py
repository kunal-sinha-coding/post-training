def max_subarray_product(nums):
    # Initialize variables to store the maximum and minimum products up to the current position
    max_product = nums[0]
    min_product = nums[0]
    result = nums[0]
    
    # Iterate through the array starting from the second element
    for i in range(1, len(nums)):
        # Update the maximum and minimum products considering the current element
        max_product = max(nums[i], max_product * nums[i])
        min_product = min(nums[i], min_product * nums[i])
        
        # Update the result with the maximum product found so far
        result = max(result, max_product)
    
    return result