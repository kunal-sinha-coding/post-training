def get_max_sum(n):
    # Base case: if n is 0 or 1, return n itself
    if n == 0 or n == 1:
        return n
    # Recursive case: find the maximum sum using the given equation
    else:
        # Calculate the maximum sum by considering the sum of the three largest numbers less than or equal to n
        return max(get_max_sum(n/2), get_max_sum(n/3), get_max_sum(n/4), get_max_sum(n/5))
