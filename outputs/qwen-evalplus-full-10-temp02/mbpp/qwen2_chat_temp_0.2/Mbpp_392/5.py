def get_max_sum(n):
    """
    Find the maximum sum possible by using the given equation f(n) = max( (f(n/2) + f(n/3) + f(n/4) + f(n/5)), n).
    
    Args:
    n (int): The input number.
    
    Returns:
    int: The maximum sum possible.
    """
    # Base case: if n is 0 or 1, the sum is n itself
    if n == 0 or n == 1:
        return n
    
    # Recursive case: calculate the maximum sum using the given equation
    return max(get_max_sum(n/2), get_max_sum(n/3), get_max_sum(n/4), get_max_sum(n/5)) + n