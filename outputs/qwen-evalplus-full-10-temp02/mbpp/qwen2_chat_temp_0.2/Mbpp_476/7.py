def big_sum(arr):
    # Initialize the maximum and minimum values with the first element of the array
    max_value = arr[0]
    min_value = arr[0]
    
    # Iterate through the array to find the maximum and minimum values
    for num in arr:
        if num > max_value:
            max_value = num
        if num < min_value:
            min_value = num
    
    # Return the sum of the largest and smallest values
    return max_value + min_value