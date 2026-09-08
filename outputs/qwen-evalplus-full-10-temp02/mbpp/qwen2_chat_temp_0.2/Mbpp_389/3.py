def find_lucas(n):
    # Base case: the first and second lucas numbers are 2
    if n == 1:
        return 2
    elif n == 2:
        return 1
    else:
        # Initialize the first two lucas numbers
        lucas_1 = 2
        lucas_2 = 1
        # Calculate the lucas number for n > 2
        for i in range(3, n + 1):
            lucas_next = lucas_1 + lucas_2
            lucas_1 = lucas_2
            lucas_2 = lucas_next
        return lucas_2