def max_sum(arr):
    # Initialize the maximum sum to the first element of the array
    max_sum = arr[0]
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Update the maximum sum if the current element is greater than the previous one
        if arr[i] > arr[i - 1]:
            max_sum = max(max_sum, arr[i])
    # Return the maximum sum found
    return max_sum