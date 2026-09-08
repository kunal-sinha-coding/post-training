def next_Perfect_Square(n):
    # Start from the next perfect square greater than n
    i = n + 1
    while i * i <= n:
        i += 1
    return i * i