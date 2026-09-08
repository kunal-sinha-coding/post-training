def max_sum(arr):
    # Initialize the maximum sum to 0
    max_sum = 0
    # Iterate through the array
    for i in range(1, len(arr)):
        # Check if the current element is greater than the previous one
        if arr[i] > arr[i - 1]:
            # Update the maximum sum if the current element is greater
            max_sum = max(max_sum, arr[i])
    # Return the maximum sum found
    return max_sum