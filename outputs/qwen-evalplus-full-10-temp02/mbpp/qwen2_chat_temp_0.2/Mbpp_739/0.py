def find_Index(n):
    # Initialize the smallest triangular number with n digits to a large number
    smallest_triangular = 10**n * (n + 1) // 2
    # Initialize the index of the smallest triangular number to -1
    index = -1
    # Iterate through possible triangular numbers
    for i in range(1, smallest_triangular):
        # Calculate the triangular number
        triangular = i * (i + 1) // 2
        # Check if the triangular number is less than the current smallest triangular number
        if triangular < smallest_triangular:
            # Update the smallest triangular number and its index
            smallest_triangular = triangular
            index = i
    # Return the index of the smallest triangular number
    return index