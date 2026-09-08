def maxAverageOfPath(matrix):
    # Initialize variables to store the maximum average and the current path
    max_avg = float('-inf')
    current_path = []
    
    # Define the directions for moving right and down
    directions = [(0, 1), (1, 0)]
    
    # Start the DFS from the top-left cell
    def dfs(x, y):
        # If the current cell is the bottom-right cell, calculate the average
        if x == len(matrix) - 1 and y == len(matrix[0]) - 1:
            avg = sum(matrix[x][y]) / (x + y + 1)
            # Update the maximum average if the current average is greater
            if avg > max_avg:
                max_avg = avg
                current_path = [matrix[x][y]]
            return
        
        # Explore all possible directions
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            # If the new cell is within bounds and not visited
            if 0 <= nx < len(matrix) and 0 <= ny < len(matrix[0]) and (nx, ny) not in current_path:
                current_path.append(matrix[nx][ny])
                dfs(nx, ny)
                current_path.pop()
    
    # Start the DFS from the top-left cell
    dfs(0, 0)
    
    return max_avg