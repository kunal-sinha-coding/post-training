def maxAverageOfPath(matrix):
    """
    Given a square matrix of size N*N given as a list of lists, where each cell is associated with a specific cost. A path is defined as a specific sequence of cells that starts from the top-left cell move only right or down and ends on bottom right cell. We want to find a path with the maximum average over all existing paths. Average is computed as total cost divided by the number of cells visited in the path.
    """
    N = len(matrix)
    # Initialize the maximum average to a very low value
    max_avg = float('-inf')
    # Initialize the current path with the first cell
    current_path = [matrix[0][0]]
    # Iterate through each cell in the matrix
    for i in range(1, N):
        # Add the cost of the current cell to the current path
        current_path.append(matrix[i][0])
        # If the current path has more than 2 cells, calculate the average
        if len(current_path) > 2:
            avg = sum(current_path) / len(current_path)
            # Update the maximum average if the current average is greater
            if avg > max_avg:
                max_avg = avg
        # Remove the last cell from the current path
        current_path.pop()
    return max_avg