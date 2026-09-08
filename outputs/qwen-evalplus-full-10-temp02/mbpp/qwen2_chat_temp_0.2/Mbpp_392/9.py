def get_max_sum(n):
    """
    Find the maximum sum possible by using the given equation f(n) = max( (f(n/2) + f(n/3) + f(n/4) + f(n/5)), n).
    
    Args:
    n (int): The input number.
    
    Returns:
    int: The maximum sum possible.
    """
    if n == 0:
        return 0
    elif n == 1:
        return 1
    elif n == 2:
        return 2
    elif n == 3:
        return 3
    elif n == 4:
        return 4
    elif n == 5:
        return 5
    else:
        # Recursive case: sum of the maximum values of f(n/2), f(n/3), f(n/4), f(n/5)
        return max(get_max_sum(n // 2), get_max_sum(n // 3), get_max_sum(n // 4), get_max_sum(n // 5)) + n