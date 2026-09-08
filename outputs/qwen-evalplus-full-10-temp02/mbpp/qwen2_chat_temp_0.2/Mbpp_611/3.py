def max_of_nth(matrix, n):
    # Extract the n'th column from the matrix
    nth_column = [row[n] for row in matrix]
    # Find the maximum value in the n'th column
    max_value = max(nth_column)
    return max_value