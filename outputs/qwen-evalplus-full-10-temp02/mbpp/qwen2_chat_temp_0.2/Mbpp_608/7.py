def bell_Number(n):
    # Base case: Bell number for n = 0 is 1
    if n == 0:
        return 1
    # Base case: Bell number for n = 1 is 1
    elif n == 1:
        return 1
    # Initialize the first two Bell numbers
    bell_0 = 1
    bell_1 = 1
    # Initialize the result
    result = 0
    # Calculate Bell numbers iteratively
    for i in range(2, n + 1):
        result += bell_0 * bell_1
        # Swap the values of bell_0 and bell_1
        bell_0, bell_1 = bell_1, bell_0
    return result