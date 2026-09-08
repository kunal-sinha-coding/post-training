def largest_subset(nums):
    # Sort the list to make it easier to find the largest divisible pair
    nums.sort()
    # Initialize the result with the first element of the sorted list
    result = [nums[0]]
    # Iterate through the sorted list starting from the second element
    for num in nums[1:]:
        # Check if the current number is divisible by the last element in the result
        if num % result[-1] == 0:
            # If it is, add the current number to the result
            result.append(num)
    # Return the length of the result list, which represents the size of the largest subset
    return len(result)