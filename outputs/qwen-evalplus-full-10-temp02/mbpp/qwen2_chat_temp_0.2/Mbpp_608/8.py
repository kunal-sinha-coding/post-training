def bell_Number(n):
    # Base case: if n is 0 or 1, the Bell number is 1
    if n == 0 or n == 1:
        return 1
    # Initialize the Bell number array
    bell = [0] * (n + 1)
    bell[0] = bell[1] = 1
    # Fill the Bell number array using the recurrence relation
    for i in range(2, n + 1):
        bell[i] = bell[i - 1] + bell[i - 2]
    return bell[n]