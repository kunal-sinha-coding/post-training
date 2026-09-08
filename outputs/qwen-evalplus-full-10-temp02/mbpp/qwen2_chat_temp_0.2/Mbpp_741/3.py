def all_Characters_Same(s):
    # Check if the length of the string is 0 or 1
    if len(s) <= 1:
        return True
    # Iterate through the string and check if all characters are the same
    for i in range(1, len(s)):
        if s[i] != s[i - 1]:
            return False
    return True