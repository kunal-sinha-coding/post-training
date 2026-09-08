def get_max_sum(n):
    # Base case: if n is 0 or 1, return n itself
    if n == 0 or n == 1:
        return n
    # Recursive case: use the given equation f(n) = max( (f(n/2) + f(n/3) + f(n/4) + f(n/5)), n )
    return max(get_max_sum(n/2), get_max_sum(n/3), get_max_sum(n/4), get_max_sum(n/5)) + n