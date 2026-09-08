def bell_Number(n):
    # Base case: if n is 0 or 1, the Bell number is 0
    if n == 0 or n == 1:
        return 0
    # Initialize the Bell number array
    bell = [0] * (n + 1)
    # Base case: bell[0] = 1
    bell[0] = 1
    # Fill the Bell number array
    for i in range(1, n + 1):
        bell[i] = bell[i - 1] + bell[i - 2]
    return bell[n]
