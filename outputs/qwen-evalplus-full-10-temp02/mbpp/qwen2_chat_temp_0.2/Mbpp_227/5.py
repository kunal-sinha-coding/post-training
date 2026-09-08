def min_of_three(a, b, c):
    # Compare the three numbers and return the minimum
    if a < b and a < c:
        return a
    elif b < a and b < c:
        return b
    else:
        return c