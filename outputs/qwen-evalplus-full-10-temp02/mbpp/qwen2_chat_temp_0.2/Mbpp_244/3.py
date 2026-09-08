def next_Perfect_Square(n):
    # Start from the square root of n and move upwards
    for i in range(int(n**0.5) + 1):
        # Check if the square of i is greater than n
        if i*i > n:
            # Return the square of i plus 1
            return i*i + 1
    # If no perfect square is found, return n itself
    return n
