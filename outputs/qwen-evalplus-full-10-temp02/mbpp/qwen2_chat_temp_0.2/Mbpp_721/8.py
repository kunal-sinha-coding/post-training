def maxAverageOfPath(matrix):
    # Initialize variables to keep track of the maximum average and the current path
    max_avg = float('-inf')
    current_path = []
    
    # Define the directions for moving right and down
    directions = [(0, 1), (1, 0)]
    
    # Iterate through each cell in the matrix
    for i in range(len(matrix)):
        for j in range(len(matrix[0])):
            # If the current cell is the bottom-right cell, calculate the average of the current path
            if i == len(matrix) - 1 and j == len(matrix[0]) - 1:
                current_avg = sum(matrix[i][j]) / (1 + len(matrix[i]))
                # Update the maximum average if the current average is greater
                if current_avg > max_avg:
                    max_avg = current_avg
                    current_path = [matrix[i][j]]
            else:
                # Recursively calculate the average of the current path
                for dx, dy in directions:
                    nx, ny = i + dx, j + dy
                    if 0 <= nx < len(matrix) and 0 <= ny < len(matrix[0]):
                        current_path.append(matrix[nx][ny])
                        # Recursively calculate the average of the current path
                        current_avg = (current_avg * 1 + matrix[nx][ny]) / (1 + len(current_path))
                        # Update the maximum average if the current average is greater
                        if current_avg > max_avg:
                            max_avg = current_avg
                            current_path = [matrix[nx][ny]]
    
    return max_avg