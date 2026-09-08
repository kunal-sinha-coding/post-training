def find_Index(n):
    # Initialize the smallest triangular number with n digits to a large number
    smallest_triangular = 10**n - 1
    # Initialize the index to 0
    index = 0
    
    # Iterate through possible triangular numbers
    for i in range(1, smallest_triangular):
        # Calculate the sum of the first i natural numbers
        sum_of_numbers = i * (i + 1) // 2
        # Check if the sum of numbers is greater than or equal to n
        if sum_of_numbers >= n:
            # Update the smallest triangular number and its index
            smallest_triangular = sum_of_numbers
            index = i
    
    # Return the index of the smallest triangular number
    return index