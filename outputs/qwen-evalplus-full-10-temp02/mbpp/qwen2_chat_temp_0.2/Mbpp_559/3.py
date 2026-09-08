def max_sub_array_sum(arr, n):
    # Initialize variables to store the maximum sum found so far and the current sum
    max_sum = arr[0]
    current_sum = arr[0]
    
    # Iterate through the array starting from the second element
    for i in range(1, n):
        # Update the current sum to be the maximum of the current element itself or the sum of the current element and the current sum
        current_sum = max(arr[i], current_sum + arr[i])
        
        # Update the maximum sum found so far if the current sum is greater
        max_sum = max(max_sum, current_sum)
    
    # Return the maximum sum found
    return max_sum