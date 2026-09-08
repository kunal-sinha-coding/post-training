def largest_subset(nums):
    # Sort the list to make it easier to find the largest subset
    nums.sort()
    # Initialize the maximum subset size to 1
    max_subset = 1
    # Iterate through the sorted list
    for i in range(1, len(nums)):
        # If the current number is divisible by the previous number, increase the subset size
        if nums[i] % nums[i-1] == 0:
            max_subset += 1
    # Return the maximum subset size
    return max_subset