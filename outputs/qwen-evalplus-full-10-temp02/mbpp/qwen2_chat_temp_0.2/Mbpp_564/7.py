def count_Pairs(nums, n):
    # Initialize a counter for pairs
    count = 0
    # Iterate through each element in the list
    for i in range(n):
        # Iterate through each element in the list starting from the next element
        for j in range(i + 1, n):
            # Check if both elements are unequal
            if nums[i] != nums[j]:
                # Increment the counter if they are unequal
                count += 1
    # Return the total count of pairs
    return count