def big_sum(arr):
    # Initialize the maximum and minimum values with the first element of the array
    max_val = arr[0]
    min_val = arr[0]
    
    # Iterate through the array to find the maximum and minimum values
    for num in arr:
        if num > max_val:
            max_val = num
        if num < min_val:
            min_val = num
    
    # Return the sum of the maximum and minimum values
    return max_val + min_val