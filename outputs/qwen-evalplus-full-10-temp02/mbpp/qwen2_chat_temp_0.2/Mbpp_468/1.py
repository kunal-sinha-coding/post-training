def max_product(nums):
    # Initialize variables to store the maximum product and the minimum product
    max_product = nums[0]
    min_product = nums[0]
    # Initialize the result to store the maximum product found
    result = nums[0]
    
    # Iterate through the array starting from the second element
    for i in range(1, len(nums)):
        # Update the maximum product if the current element is greater
        if nums[i] > max_product:
            max_product = nums[i]
        # Update the minimum product if the current element is smaller
        if nums[i] < min_product:
            min_product = nums[i]
        # Calculate the maximum product by multiplying the current element with the minimum product
        result = max(result, max_product * min_product)
    
    return result