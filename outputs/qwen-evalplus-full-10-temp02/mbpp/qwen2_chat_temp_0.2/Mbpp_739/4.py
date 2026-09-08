def find_Index(n):
    # Initialize the smallest triangular number as 0
    smallest_triangular = 0
    # Iterate through possible triangular numbers
    for i in range(1, n + 1):
        # Calculate the triangular number
        triangular = i * (i + 1) // 2
        # Check if the triangular number is greater than the smallest triangular number found so far
        if triangular > smallest_triangular:
            # Update the smallest triangular number
            smallest_triangular = triangular
    # Return the index of the smallest triangular number
    return smallest_triangular - 1