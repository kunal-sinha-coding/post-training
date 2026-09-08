def count_Pairs(arr, n):
    # Initialize a counter for pairs
    count = 0
    # Iterate through each element in the array
    for i in range(n):
        # Iterate through each element in the array starting from i+1
        for j in range(i+1, n):
            # Check if both elements are unequal
            if arr[i] != arr[j]:
                # Increment the counter for each pair
                count += 1
    # Return the total count of pairs
    return count