def max_of_nth(matrix, n):
    # Initialize the maximum value to the first element of the n-th column
    max_value = matrix[0][n-1]
    
    # Iterate through each row in the matrix
    for row in matrix:
        # Update the maximum value if the current element in the n-th column is greater
        if row[n-1] > max_value:
            max_value = row[n-1]
    
    # Return the maximum value found
    return max_value