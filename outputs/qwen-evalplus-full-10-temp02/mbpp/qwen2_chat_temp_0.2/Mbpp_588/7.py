def big_diff(nums):
    # Initialize the maximum and minimum values with the first element of the list
    max_val = min_val = nums[0]
    
    # Iterate through the list starting from the second element
    for num in nums[1:]:
        # Update the maximum value if the current number is greater
        if num > max_val:
            max_val = num
        # Update the minimum value if the current number is less
        if num < min_val:
            min_val = num
    
    # Calculate and return the difference between the maximum and minimum values
    return max_val - min_val