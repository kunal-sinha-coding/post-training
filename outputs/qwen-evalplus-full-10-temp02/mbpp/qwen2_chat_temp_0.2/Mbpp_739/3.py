def find_Index(n):
    # Initialize the smallest triangular number as 0
    smallest_triangular = 0
    # Initialize the index as 0
    index = 0
    
    # Iterate through possible triangular numbers
    for i in range(1, n + 1):
        # Calculate the triangular number
        triangular = i * (i + 1) // 2
        # Check if the triangular number is less than the smallest triangular number found so far
        if triangular < smallest_triangular:
            # Update the smallest triangular number and its index
            smallest_triangular = triangular
            index = i
    
    # Return the index of the smallest triangular number
    return index