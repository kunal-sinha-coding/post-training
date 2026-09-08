def max_sub_array_sum_repeated(arr, k, n):
    # Initialize the maximum sum to the first element of the array
    max_sum = arr[0]
    # Initialize the current sum to the first element of the array
    current_sum = arr[0]
    # Iterate through the array starting from the second element
    for i in range(1, n):
        # Update the current sum by adding the next element
        current_sum += arr[i]
        # Update the maximum sum if the current sum is greater
        if current_sum > max_sum:
            max_sum = current_sum
    # Return the maximum sum found
    return max_sum