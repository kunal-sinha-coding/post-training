def maxAverageOfPath(matrix):
    """
    Given a square matrix of size N*N given as a list of lists, where each cell is associated with a specific cost. A path is defined as a specific sequence of cells that starts from the top-left cell move only right or down and ends on bottom right cell. We want to find a path with the maximum average over all existing paths. Average is computed as total cost divided by the number of cells visited in the path.
    """
    N = len(matrix)
    # Initialize the maximum average to a very low value
    max_avg = float('-inf')
    # Iterate through each cell in the matrix
    for i in range(N):
        for j in range(N):
            # If the current cell is the top-left cell, calculate the average
            if i == 0 and j == 0:
                avg = matrix[i][j]
            # If the current cell is the bottom-right cell, calculate the average
            elif i == N-1 and j == N-1:
                avg = matrix[i][j]
            # If the current cell is not the top-left or bottom-right cell, calculate the average
            else:
                # Calculate the average of the current cell and the cell above it
                avg = (matrix[i][j] + matrix[i-1][j]) / 2
            # Update the maximum average if the current average is greater
            if avg > max_avg:
                max_avg = avg
    return max_avg