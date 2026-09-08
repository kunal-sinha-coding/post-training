def max_product(nums):
    # Initialize variables to store the maximum product and the minimum product
    max_product = nums[0]
    min_product = nums[0]
    result = nums[0]
    
    # Iterate through the array starting from the second element
    for num in nums[1:]:
        # Update the maximum product if the current number is greater
        if num > max_product:
            max_product = num
        # Update the minimum product if the current number is smaller
        if num < min_product:
            min_product = num
        
        # Calculate the maximum product by considering the current number and the minimum product
        result = max(result, max_product * num)
    
    return result