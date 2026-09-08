def next_Perfect_Square(n):
    # Start from the next integer after n
    i = n + 1
    # While the square of i is less than or equal to n
    while i * i <= n:
        # Increment i to find the next perfect square
        i += 1
    # Return the next perfect square
    return i * i