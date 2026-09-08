def find_star_num(n):
    # Base case: the first star number is 1
    if n == 1:
        return 1
    # Recursive case: the n'th star number is the sum of the first n natural numbers
    else:
        return n * (n + 1) // 2