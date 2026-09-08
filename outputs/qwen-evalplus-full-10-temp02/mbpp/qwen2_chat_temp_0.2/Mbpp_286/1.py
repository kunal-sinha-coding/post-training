def max_sub_array_sum_repeated(arr, k, n):
    # Initialize the maximum sum to the first element of the array
    max_sum = arr[0]
    # Initialize the current sum to the first element of the array
    current_sum = arr[0]
    # Iterate through the array starting from the second element
    for i in range(1, n):
        # Update the current sum by adding the next element to it
        current_sum += arr[i]
        # Update the maximum sum if the current sum is greater
        max_sum = max(max_sum, current_sum)
        # If the current sum is less than 0, reset it to 0
        if current_sum < 0:
            current_sum = 0
    # Return the maximum sum found
    return max_sum