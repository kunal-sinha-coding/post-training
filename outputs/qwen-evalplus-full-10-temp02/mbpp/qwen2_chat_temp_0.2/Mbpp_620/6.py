def largest_subset(nums):
    # Sort the list to make it easier to find the largest subset
    nums.sort()
    # Initialize the maximum subset size to 0
    max_subset = 0
    # Iterate through the sorted list
    for num in nums:
        # If the current number is divisible by the previous number, add it to the subset
        if num % nums[-1] == 0:
            max_subset += 1
    # Return the maximum subset size
    return max_subset