def odd_length_sum(arr):
    # Initialize the sum to 0
    total_sum = 0
    # Iterate through the array
    for i in range(len(arr)):
        # Check if the length of the current subarray is odd
        if i % 2 != 0:
            # Add the current element to the total sum
            total_sum += arr[i]
    # Return the total sum of odd length subarrays
    return total_sum