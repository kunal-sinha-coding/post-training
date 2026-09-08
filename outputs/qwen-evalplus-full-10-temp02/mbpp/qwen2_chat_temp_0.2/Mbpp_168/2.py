def frequency(lst, num):
    # Initialize a counter to zero
    count = 0
    # Iterate through each element in the list
    for i in lst:
        # Check if the current element matches the target number
        if i == num:
            # Increment the counter if it does
            count += 1
    # Return the total count of occurrences
    return count