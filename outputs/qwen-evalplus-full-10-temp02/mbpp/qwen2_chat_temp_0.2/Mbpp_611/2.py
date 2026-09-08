def max_of_nth(matrix, n):
    # Extract the n'th column from each row
    column_values = [row[n-1] for row in matrix]
    # Return the maximum value from the column values
    return max(column_values)