def catalan_number(n):
    # Base case: the first Catalan number is 1
    if n == 0:
        return 1
    # Initialize the first two Catalan numbers
    a, b = 1, 1
    # Calculate the Catalan numbers iteratively
    for i in range(2, n + 1):
        c = a + b
        a, b = b, c
    return c