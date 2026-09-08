def bell_Number(n):
    # Base case: Bell number for n = 0 is 1
    if n == 0:
        return 1
    # Recursive case: Bell number for n = 1 is 1
    elif n == 1:
        return 1
    # Recursive case: Bell number for n > 1 is the sum of Bell numbers for n-1 and n-2
    else:
        return bell_Number(n-1) + bell_Number(n-2)