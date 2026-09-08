def maxAverageOfPath(matrix):
    # Initialize the maximum average to a very low value
    max_avg = float('-inf')
    
    # Iterate through each cell in the matrix
    for i in range(len(matrix)):
        for j in range(len(matrix[0])):
            # Calculate the cost of moving to the next cell
            cost = matrix[i][j]
            
            # Check if the current cell is the top-left cell
            if i == 0 and j == 0:
                # If it is, add the cost to the current path
                current_path = [cost]
                # Calculate the average of the current path
                current_avg = sum(current_path) / len(current_path)
                # Update the maximum average if the current average is greater
                if current_avg > max_avg:
                    max_avg = current_avg
    
    return max_avg