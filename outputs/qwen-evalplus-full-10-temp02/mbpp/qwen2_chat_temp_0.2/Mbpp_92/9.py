def is_undulating(n):
    # Check if the number is a palindrome
    if str(n) == str(n)[::-1]:
        # Check if the number is a palindrome of length 2 or more
        if len(str(n)) > 1:
            # Check if the number is a palindrome of length 2 or more
            if str(n) == str(n)[1:-1]:
                return True
    return False