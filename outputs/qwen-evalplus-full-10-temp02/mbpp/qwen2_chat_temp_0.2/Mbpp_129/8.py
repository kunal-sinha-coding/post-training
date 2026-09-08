def magic_square_test(matrix):
    # Check if the matrix is a square
    if len(matrix) != len(matrix[0]):
        return False
    
    # Calculate the sum of each row
    row_sums = sum(row) for row in matrix
    
    # Calculate the sum of each column
    col_sums = sum(matrix[i][j] for i in range(len(matrix)) for j in range(len(matrix[0]))
    
    # Calculate the sum of the main diagonal
    main_diag_sum = sum(matrix[i][i] for i in range(len(matrix)))
    
    # Calculate the sum of the secondary diagonal
    sec_diag_sum = sum(matrix[i][len(matrix) - 1 - i] for i in range(len(matrix)))
    
    # Check if all row sums, column sums, main diagonal sum, and secondary diagonal sum are equal
    return row_sums == col_sums == main_diag_sum == sec_diag_sum