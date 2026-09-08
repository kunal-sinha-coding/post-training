def bell_Number(n):
    # Base case: Bell number for n = 0 is 1
    if n == 0:
        return 1
    # Initialize the first two Bell numbers
    bell_0 = 1
    bell_1 = 1
    # Calculate Bell numbers iteratively
    for i in range(2, n + 1):
        # Bell number for i is the sum of Bell numbers for i-1 and i-2
        bell_i = bell_0 + bell_1
        # Update Bell numbers for the next iteration
        bell_0 = bell_1
        bell_1 = bell_i
    return bell_1