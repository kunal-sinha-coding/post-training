def catalan_number(n):
    # Base case: if n is 0 or 1, return 1
    if n == 0 or n == 1:
        return 1
    # Initialize the first two Catalan numbers
    catalan_0 = 1
    catalan_1 = 1
    # Calculate the nth Catalan number iteratively
    for i in range(2, n + 1):
        # Calculate the next Catalan number as the sum of the two previous ones
        catalan_next = catalan_0 + catalan_1
        # Update the previous two Catalan numbers
        catalan_0 = catalan_1
        catalan_1 = catalan_next
    return catalan_1