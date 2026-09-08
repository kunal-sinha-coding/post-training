def largest_subset(nums):
    # Sort the list in ascending order
    nums.sort()
    # Initialize the maximum subset size to 1
    max_subset_size = 1
    # Initialize the current subset size to 1
    current_subset_size = 1
    # Iterate through the sorted list
    for i in range(1, len(nums)):
        # If the current number is divisible by the previous number, increase the current subset size
        if nums[i] % nums[i-1] == 0:
            current_subset_size += 1
        # Update the maximum subset size if the current subset size is greater
        if current_subset_size > max_subset_size:
            max_subset_size = current_subset_size
    return max_subset_size