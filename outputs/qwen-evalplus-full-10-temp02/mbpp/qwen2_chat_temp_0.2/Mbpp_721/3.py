def maxAverageOfPath(matrix):
    # Initialize variables to store the maximum average and the path
    max_avg = float('-inf')
    path = []
    
    # Iterate through each cell in the matrix
    for i in range(len(matrix)):
        for j in range(len(matrix[0])):
            # Check if the current cell is the starting cell
            if i == 0 and j == 0:
                # Start the path with the current cell
                path.append((i, j))
                # Calculate the cost of the path
                cost = matrix[i][j]
            else:
                # Move to the right or down
                next_x = i + 1
                next_y = j + 1
                # If the next cell is within bounds and not visited
                if 0 <= next_x < len(matrix) and 0 <= next_y < len(matrix[0]) and (next_x, next_y) not in path:
                    # Add the next cell to the path
                    path.append((next_x, next_y))
                    # Calculate the cost of the path
                    cost = matrix[next_x][next_y]
                    # Update the maximum average if the current path has a higher average
                    if cost / (i + 1) > max_avg:
                        max_avg = cost / (i + 1)
    
    # Return the maximum average found
    return max_avg