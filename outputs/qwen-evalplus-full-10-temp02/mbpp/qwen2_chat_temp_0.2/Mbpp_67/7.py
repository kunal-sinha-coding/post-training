def bell_number(n):
    # Base case: Bell number of 0 is 1
    if n == 0:
        return 1
    # Initialize the result to 0
    result = 0
    # Iterate through each number from 1 to n
    for i in range(1, n + 1):
        # Calculate the Bell number for the current number
        result += bell_number(i - 1)
    return result