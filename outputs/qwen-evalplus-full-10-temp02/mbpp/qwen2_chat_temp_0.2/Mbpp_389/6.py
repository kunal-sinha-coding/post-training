def find_lucas(n):
    # Base case: the first two lucas numbers are 2 and 1
    if n == 0:
        return 2
    elif n == 1:
        return 1
    else:
        # Recursive case: the nth lucas number is the sum of the (n-1)th and (n-2)th lucas numbers
        return find_lucas(n-1) + find_lucas(n-2)