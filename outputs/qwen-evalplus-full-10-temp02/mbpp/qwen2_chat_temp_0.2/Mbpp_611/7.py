def max_of_nth(matrix, n):
    # Extract the n'th column from each row
    column_n = [row[n] for row in matrix]
    # Return the maximum value from the column
    return max(column_n)