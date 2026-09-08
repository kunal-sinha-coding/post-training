def find_Index(n):
    # Initialize the smallest triangular number with n digits to a large number
    smallest_triangular = 10**n * (n + 1) // 2
    
    # Iterate through numbers starting from 1 to find the smallest triangular number
    for i in range(1, n + 1):
        # Calculate the triangular number for the current number
        triangular = i * (i + 1) // 2
        
        # Check if the triangular number is smaller than the smallest triangular number found so far
        if triangular < smallest_triangular:
            smallest_triangular = triangular
    
    # Return the index of the smallest triangular number
    return smallest_triangular - 1