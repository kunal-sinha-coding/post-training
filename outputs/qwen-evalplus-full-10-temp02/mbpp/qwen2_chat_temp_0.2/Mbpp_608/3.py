def bell_Number(n):
    # Base case: bell numbers for n = 0 and n = 1 are 1
    if n == 0 or n == 1:
        return 1
    # Initialize the first two bell numbers
    bell_0 = 1
    bell_1 = 1
    # Calculate the bell numbers iteratively up to n
    for i in range(2, n + 1):
        # Calculate the next bell number as the sum of the previous two bell numbers
        bell_next = bell_0 + bell_1
        # Update the previous two bell numbers
        bell_0 = bell_1
        bell_1 = bell_next
    return bell_1