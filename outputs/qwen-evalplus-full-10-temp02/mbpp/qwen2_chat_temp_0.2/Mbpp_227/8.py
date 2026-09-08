def min_of_three(a, b, c):
    # Initialize the minimum value with the first number
    min_value = a
    
    # Compare the third number with the current minimum value
    if b < min_value:
        min_value = b
    
    # Compare the first number with the current minimum value
    if c < min_value:
        min_value = c
    
    # Return the minimum value found
    return min_value