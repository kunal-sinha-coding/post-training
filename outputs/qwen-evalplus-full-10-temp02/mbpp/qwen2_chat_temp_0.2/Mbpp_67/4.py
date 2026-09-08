def bell_number(n):
    # Base case: Bell number of 0 is 1
    if n == 0:
        return 1
    # Base case: Bell number of 1 is 1
    elif n == 1:
        return 1
    # Initialize the result
    result = 0
    # Iterate through all possible partitions
    for i in range(2, n + 1):
        # Add the number of ways to partition the set to the result
        result += bell_number(i - 1)
    return result