def find_Index(n):
    # Initialize the smallest triangular number as 1
    smallest_triangular = 1
    # Initialize the index to 0
    index = 0
    
    # Loop through the digits of n
    for i in range(1, n + 1):
        # Calculate the triangular number
        triangular = i * (i + 1) // 2
        # Check if the triangular number is smaller than the current smallest triangular number
        if triangular < smallest_triangular:
            # Update the smallest triangular number and the index
            smallest_triangular = triangular
            index = i
    
    # Return the index of the smallest triangular number
    return index