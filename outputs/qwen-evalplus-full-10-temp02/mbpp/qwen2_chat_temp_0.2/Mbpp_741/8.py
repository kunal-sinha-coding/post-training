def all_Characters_Same(s):
    # Check if the length of the string is less than 2
    if len(s) < 2:
        return True
    # Iterate through the string and check if all characters are the same
    for i in range(len(s)):
        if s[i] != s[i + 1]:
            return False
    return True