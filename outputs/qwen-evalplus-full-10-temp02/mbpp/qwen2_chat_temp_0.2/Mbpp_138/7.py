def is_Sum_Of_Powers_Of_Two(n):
    # Initialize a variable to store the result
    result = False
    # Loop through possible powers of 2
    for i in range(0, n + 1):
        # Check if the current power of 2 is less than or equal to n
        if i ** 2 <= n:
            # If it is, set the result to True
            result = True
            # Break out of the loop as we found a valid power
            break
    # Return the result
    return result