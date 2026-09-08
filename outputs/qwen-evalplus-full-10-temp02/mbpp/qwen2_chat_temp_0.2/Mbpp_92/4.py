def is_undulating(n):
    # Check if the number is a palindrome
    if str(n) == str(n)[::-1]:
        # Check if the number is a palindrome with at least one odd digit
        for i in range(len(str(n))):
            if int(str(n)[i]) % 2 != 0:
                return False
        return True
    else:
        return False