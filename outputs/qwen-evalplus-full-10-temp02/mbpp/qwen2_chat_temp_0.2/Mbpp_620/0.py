def largest_subset(nums):
    # Sort the list to make it easier to find the largest subset
    nums.sort()
    # Initialize the maximum subset size to 1
    max_subset = 1
    # Initialize the current subset size to 1
    current_subset = 1
    
    # Iterate through the sorted list
    for i in range(1, len(nums)):
        # If the current number is divisible by the previous number, increment the current subset size
        if nums[i] % nums[i-1] == 0:
            current_subset += 1
        # Update the maximum subset size if the current subset size is greater
        max_subset = max(max_subset, current_subset)
    
    return max_subset