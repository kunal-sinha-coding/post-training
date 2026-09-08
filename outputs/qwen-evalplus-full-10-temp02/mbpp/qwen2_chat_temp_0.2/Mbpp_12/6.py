def sort_matrix(matrix):
    # Sort the matrix based on the sum of its rows
    sorted_matrix = sorted(matrix, key=lambda row: sum(row))
    return sorted_matrix