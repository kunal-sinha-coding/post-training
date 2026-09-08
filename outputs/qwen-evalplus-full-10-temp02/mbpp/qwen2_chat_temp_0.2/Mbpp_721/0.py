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
            # If the current cell is the starting cell, start a new path
            if i == 0 and j == 0:
                path = [(i, j)]
                # Calculate the total cost of the path
                total_cost = sum(matrix[i][j])
                # Calculate the number of cells visited in the path
                visited_cells = 1
            else:
                # If the current cell is not the starting cell, add the current cell to the path
                path.append((i, j))
                # Calculate the total cost of the path
                total_cost += matrix[i][j]
                # Calculate the number of cells visited in the path
                visited_cells += 1
            # Calculate the average of the path
            avg = total_cost / visited_cells
            # Update the maximum average if the current average is greater
            if avg > max_avg:
                max_avg = avg
    return max_avg