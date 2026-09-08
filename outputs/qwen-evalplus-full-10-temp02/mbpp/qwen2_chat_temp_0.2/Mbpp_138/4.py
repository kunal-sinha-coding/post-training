def is_Sum_Of_Powers_Of_Two(n):
    # Initialize a variable to store the result
    result = False
    # Iterate through possible powers of 2
    for i in range(1, n + 1):
        # Check if the current power of 2 is less than or equal to n
        if i <= n:
            # If it is, add the current power of 2 to the result
            result = True
    return result