def bell_number(n):
    # Base case: if n is 0, there is only one way to partition the set
    if n == 0:
        return 1
    # Recursive case: the number of ways to partition the set is the sum of the number of ways to partition the set with n-1 elements
    else:
        return bell_number(n-1) + bell_number(n-2)