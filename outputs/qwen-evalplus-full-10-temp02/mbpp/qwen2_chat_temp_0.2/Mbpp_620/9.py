def largest_subset(nums):
    # Sort the list to make it easier to find the largest divisible subset
    nums.sort()
    # Initialize the result with the first element of the sorted list
    result = [nums[0]]
    # Iterate through the sorted list starting from the second element
    for i in range(1, len(nums)):
        # Check if the current element is divisible by the last element in the result
        if nums[i] % result[-1] == 0:
            # If it is, add the current element to the result
            result.append(nums[i])
    # Return the size of the result list, which represents the largest divisible subset
    return len(result)