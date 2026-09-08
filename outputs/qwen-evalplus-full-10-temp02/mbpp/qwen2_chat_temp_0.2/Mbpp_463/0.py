def max_subarray_product(nums):
    # Initialize variables to store the maximum and minimum products up to the current position
    max_product = min_product = nums[0]
    # Iterate through the array starting from the second element
    for num in nums[1:]:
        # Update the maximum product considering the current number
        max_product = max(num, max_product * num)
        # Update the minimum product considering the current number
        min_product = min(num, min_product * num)
        # Update the maximum product if the current product is greater
        max_product = max(max_product, num)
    # Return the maximum product found
    return max_product