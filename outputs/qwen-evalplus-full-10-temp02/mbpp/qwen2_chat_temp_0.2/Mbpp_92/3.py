def is_undulating(n):
    # Check if the number is a palindrome
    if str(n) == str(n)[::-1]:
        # Check if the number has an odd number of digits
        if len(str(n)) % 2 != 0:
            return True
    return False