def min_of_three(a, b, c):
    # Initialize the minimum value with the first number
    min_value = a
    
    # Check if the second number is smaller than the minimum value
    if b < min_value:
        min_value = b
    
    # Check if the third number is smaller than the minimum value
    if c < min_value:
        min_value = c
    
    # Return the minimum value found
    return min_value