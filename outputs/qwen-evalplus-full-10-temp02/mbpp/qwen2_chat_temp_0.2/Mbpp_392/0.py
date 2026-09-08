def get_max_sum(n):
    # Base case: if n is 0 or 1, the maximum sum is n itself
    if n == 0 or n == 1:
        return n
    
    # Recursive case: find the maximum sum of the three largest numbers in the list
    max_sum = max(f(n/2) + f(n/3) + f(n/4) + f(n/5), n)
    
    return max_sum