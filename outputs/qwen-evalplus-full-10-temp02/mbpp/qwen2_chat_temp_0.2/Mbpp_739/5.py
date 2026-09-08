def find_Index(n):
    # Initialize the smallest triangular number with n digits to a large number
    smallest_triangular = 10**n * (n + 1) // 2
    
    # Iterate through possible triangular numbers
    for i in range(1, smallest_triangular):
        # Calculate the triangular number
        triangular = i * (i + 1) // 2
        
        # Check if the triangular number has n digits
        if len(str(triangular)) == n:
            # Update the smallest triangular number if the current one is smaller
            smallest_triangular = triangular
    
    # Return the index of the smallest triangular number
    return smallest_triangular - 1