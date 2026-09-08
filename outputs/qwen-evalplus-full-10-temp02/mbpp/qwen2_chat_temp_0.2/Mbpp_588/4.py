def big_diff(numbers):
    # Initialize the maximum and minimum values with the first element of the list
    max_value = min_value = numbers[0]
    
    # Iterate through the list starting from the second element
    for num in numbers[1:]:
        # Update max_value if the current number is greater
        if num > max_value:
            max_value = num
        # Update min_value if the current number is smaller
        if num < min_value:
            min_value = num
    
    # Return the difference between max_value and min_value
    return max_value - min_value