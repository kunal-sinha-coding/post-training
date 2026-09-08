def big_diff(lst):
    # Initialize the maximum and minimum values with the first element of the list
    max_val = lst[0]
    min_val = lst[0]
    
    # Iterate through the list to find the maximum and minimum values
    for num in lst:
        if num > max_val:
            max_val = num
        if num < min_val:
            min_val = num
    
    # Calculate and return the difference between the maximum and minimum values
    return max_val - min_val