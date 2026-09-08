def is_undulating(n):
    # Check if the number is a perfect square
    if int(n**0.5)**2 == n:
        # Check if the number is a palindrome
        return str(n) == str(n)[::-1]
    return False