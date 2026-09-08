def frequency(lst, n):
    # Initialize a counter to zero
    count = 0
    # Iterate through each element in the list
    for i in lst:
        # Check if the current element matches the target number
        if i == n:
            # Increment the counter if a match is found
            count += 1
    # Return the total count of occurrences
    return count