def next_Perfect_Square(n):
    # Start from the next integer greater than n
    i = n + 1
    # Check if the square of i is greater than n
    while i * i <= n:
        i += 1
    # Return the square of i
    return i * i