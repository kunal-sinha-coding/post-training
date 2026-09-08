def max_sum(arr):
    # Initialize the maximum sum to 0
    max_sum = 0
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Check if the current element is greater than the previous one
        if arr[i] > arr[i - 1]:
            # Update the maximum sum by adding the current element to the previous maximum sum
            max_sum += arr[i]
        # If the current element is less than the previous one
        else:
            # Update the maximum sum by subtracting the previous maximum sum from the current element
            max_sum -= arr[i - 1]
    # Return the maximum sum found
    return max_sum