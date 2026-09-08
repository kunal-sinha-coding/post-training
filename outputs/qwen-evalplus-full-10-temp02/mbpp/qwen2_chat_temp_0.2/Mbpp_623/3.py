def nth_nums(nums, n):
    # Initialize an empty list to store the results
    result = []
    # Iterate through each number in the input list
    for num in nums:
        # Calculate the n-th power of the current number
        power = num ** n
        # Append the result to the list
        result.append(power)
    # Return the list of results
    return result