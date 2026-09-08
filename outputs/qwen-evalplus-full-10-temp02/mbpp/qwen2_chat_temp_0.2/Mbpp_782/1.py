def odd_length_sum(arr):
    # Initialize sum to 0
    sum = 0
    # Iterate through the array
    for i in range(len(arr)):
        # Check if the current index is odd
        if i % 2 != 0:
            # Calculate the sum of odd length subarrays
            sum += arr[i]
    return sum