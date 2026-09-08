def bell_Number(n):
    # Base case: Bell number for n = 0 is 1
    if n == 0:
        return 1
    # Initialize the first two Bell numbers
    bell_0 = 1
    bell_1 = 1
    # Calculate Bell numbers iteratively
    for i in range(2, n + 1):
        # Calculate the next Bell number
        bell_next = bell_0 + bell_1
        # Update the previous Bell numbers
        bell_0 = bell_1
        bell_1 = bell_next
    return bell_1