def is_Sum_Of_Powers_Of_Two(n):
    # Initialize a variable to store the result
    result = False
    # Iterate through possible powers of 2
    for i in range(1, n + 1):
        # Check if the current power of 2 equals n
        if n == i ** 2:
            # If it does, set the result to True
            result = True
            break
    # Return the result
    return result