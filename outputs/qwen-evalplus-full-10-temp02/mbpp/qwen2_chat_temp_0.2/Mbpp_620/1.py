def largest_subset(nums):
    # Initialize the maximum size of the subset to 0
    max_size = 0
    # Initialize a list to keep track of the current subset
    current_subset = []
    
    # Iterate through each number in the list
    for num in nums:
        # If the current number is divisible by the last number in the current subset
        if num % current_subset[-1] == 0:
            # Add the current number to the current subset
            current_subset.append(num)
            # Update the maximum size of the subset
            max_size = max(max_size, len(current_subset))
        else:
            # If the current number is not divisible by the last number in the current subset
            # Start a new subset with the current number
            current_subset = [num]
            # Update the maximum size of the subset
            max_size = max(max_size, len(current_subset))
    
    # Return the maximum size of the subset
    return max_size