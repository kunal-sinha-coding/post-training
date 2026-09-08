def get_max_sum(n):
    # Base case: if n is 0, the maximum sum is 0
    if n == 0:
        return 0
    # Recursive case: the maximum sum is the maximum of the sum of the two halves of n
    # plus the value of n itself
    return max(get_max_sum(n // 2) + get_max_sum(n // 3) + get_max_sum(n // 4) + get_max_sum(n // 5), n)