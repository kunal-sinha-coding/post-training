def is_polite(n):
    # Base case: if n is 1, return 1
    if n == 1:
        return 1
    # Initialize the first two polite numbers
    a = 1
    b = 2
    # Iterate to find the nth polite number
    for i in range(2, n + 1):
        # Calculate the next polite number as the sum of the previous two
        c = a + b
        # Update the previous two numbers
        a = b
        b = c
    # Return the nth polite number
    return b