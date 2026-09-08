def is_Sum_Of_Powers_Of_Two(n):
    # Initialize a variable to store the result
    result = False
    # Iterate through possible powers of 2
    for i in range(1, n + 1):
        # Check if the current power of 2 is a factor of n
        if n % i == 0:
            # If it is, set the result to True
            result = True
            # Break out of the loop as we found a factor
            break
    # Return the result
    return result