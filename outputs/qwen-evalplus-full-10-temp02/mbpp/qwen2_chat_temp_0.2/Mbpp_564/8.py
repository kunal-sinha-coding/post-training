def count_Pairs(arr, n):
    # Initialize a counter for the number of pairs
    count = 0
    # Iterate through the array
    for i in range(n):
        # Iterate through the array again, starting from i+1
        for j in range(i+1, n):
            # Check if the elements at the current positions are unequal
            if arr[i] != arr[j]:
                # Increment the counter if they are unequal
                count += 1
    # Return the total count of pairs
    return count