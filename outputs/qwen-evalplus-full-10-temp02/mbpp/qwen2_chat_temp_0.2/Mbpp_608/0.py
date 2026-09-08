def bell_Number(n):
    # Base case: Bell numbers for n = 0 and n = 1 are 0 and 1 respectively
    if n == 0 or n == 1:
        return 0
    # Initialize the first two Bell numbers
    bell_0 = 0
    bell_1 = 1
    # Initialize the result to store the Bell number
    result = 0
    # Loop to calculate Bell numbers up to n
    for i in range(2, n + 1):
        # Update the result by adding the previous two Bell numbers
        result = bell_0 + bell_1
        # Update the previous two Bell numbers
        bell_0 = bell_1
        bell_1 = result
    # Return the nth Bell number
    return result