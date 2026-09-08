def sum_series(n):
    """
    Calculate the sum (n - 2*i) from i=0 to n // 2, for instance n + (n-2) + (n-4)... (until n-x =< 0).
    
    :param n: Integer representing the upper limit of the series.
    :return: Integer representing the sum of the series.
    """
    total_sum = 0
    for i in range(n // 2 + 1):
        total_sum += (n - 2 * i)
    return total_sum
