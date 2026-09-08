def maxAverageOfPath(matrix):
    # Initialize variables to store the maximum average and the current path
    max_avg = 0
    current_path = []
    
    # Iterate through each cell in the matrix
    for i in range(len(matrix)):
        for j in range(len(matrix[0])):
            # If the current cell is the starting point, add it to the current path
            if i == 0 and j == 0:
                current_path.append(matrix[i][j])
            # If the current cell is the end point, calculate the average of the current path
            elif i == len(matrix) - 1 and j == len(matrix[0]) - 1:
                avg = sum(current_path) / len(current_path)
                # Update the maximum average if the current average is greater
                if avg > max_avg:
                    max_avg = avg
            # Otherwise, add the current cell to the current path
            else:
                current_path.append(matrix[i][j])
    
    return max_avg