def max_of_nth(matrix, n):
    # Initialize the maximum value to a very low number
    max_value = float('-inf')
    
    # Iterate through each row in the matrix
    for row in matrix:
        # Iterate through each element in the row
        for element in row:
            # Check if the current element is greater than the current maximum value
            if element > max_value:
                # Update the maximum value if the current element is greater
                max_value = element
    
    # Return the maximum value found in the nth column
    return max_value