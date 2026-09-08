def bell_number(n):
    # Base case: Bell number of 0 is 1
    if n == 0:
        return 1
    # Base case: Bell number of 1 is 1
    elif n == 1:
        return 1
    # Initialize the result to 0
    result = 0
    # Iterate from 2 to n
    for i in range(2, n + 1):
        # Calculate the Bell number for each number from 2 to n
        result += bell_number(i - 1) * bell_number(n - i)
    return result