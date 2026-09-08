def big_diff(numbers):
    # Initialize the maximum and minimum values with the first element of the list
    max_value = numbers[0]
    min_value = numbers[0]
    
    # Iterate through the list to find the maximum and minimum values
    for num in numbers:
        if num > max_value:
            max_value = num
        if num < min_value:
            min_value = num
    
    # Calculate the difference between the maximum and minimum values
    return max_value - min_value