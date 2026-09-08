def max_sum(arr):
    # Initialize the maximum sum to the first element of the array
    max_sum = arr[0]
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Update the maximum sum if the current element is greater than the maximum sum found so far
        if arr[i] > max_sum:
            max_sum = arr[i]
        # If the current element is less than the maximum sum found so far, update the maximum sum
        elif arr[i] < max_sum:
            max_sum = arr[i]
    # Return the maximum sum found
    return max_sum