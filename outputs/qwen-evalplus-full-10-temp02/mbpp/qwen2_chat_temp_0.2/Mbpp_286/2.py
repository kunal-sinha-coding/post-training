def max_sub_array_sum_repeated(arr, k, n):
    # Initialize variables to store the maximum sum found so far and the current sum
    max_sum = current_sum = arr[0]
    
    # Iterate through the array starting from the second element
    for i in range(1, n):
        # Update the current sum by adding the current element to it
        current_sum += arr[i]
        
        # If the current sum is greater than the maximum sum found so far, update max_sum
        if current_sum > max_sum:
            max_sum = current_sum
        
        # If the current sum becomes negative, reset it to zero
        if current_sum < 0:
            current_sum = 0
    
    # Return the maximum sum found
    return max_sum