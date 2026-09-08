def maxAverageOfPath(matrix):
    # Initialize variables to store the maximum average and the current path
    max_avg = float('-inf')
    current_path = []
    
    # Iterate through each cell in the matrix
    for i in range(len(matrix)):
        for j in range(len(matrix[0])):
            # If the current cell is the top-left cell, start a new path
            if i == 0 and j == 0:
                current_path.append(matrix[i][j])
            else:
                # Add the current cell's cost to the current path
                current_path.append(matrix[i][j])
                # If the current path has more than one cell, calculate the average
                if len(current_path) > 1:
                    avg = sum(current_path) / len(current_path)
                    # Update the maximum average if the current average is greater
                    if avg > max_avg:
                        max_avg = avg
    
    return max_avg