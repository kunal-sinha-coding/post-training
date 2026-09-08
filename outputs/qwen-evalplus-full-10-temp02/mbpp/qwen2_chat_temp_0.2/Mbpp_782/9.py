def odd_length_sum(arr):
    # Initialize the sum to 0
    sum = 0
    # Iterate through the array
    for i in range(len(arr)):
        # Check if the length of the current subarray is odd
        if i % 2 != 0:
            # Add the sum of the current subarray to the sum
            sum += arr[i]
    # Return the total sum of all odd length subarrays
    return sum