def big_diff(nums):
    # Initialize the maximum and minimum values with the first element of the list
    max_val = nums[0]
    min_val = nums[0]
    
    # Iterate through the list to find the maximum and minimum values
    for num in nums:
        if num > max_val:
            max_val = num
        if num < min_val:
            min_val = num
    
    # Calculate the difference between the maximum and minimum values
    diff = max_val - min_val
    
    # Return the difference
    return diff