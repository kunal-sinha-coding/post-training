def all_Characters_Same(s):
    # Check if the length of the string is less than 2
    if len(s) < 2:
        return False
    # Iterate through the string and compare each character with the next one
    for i in range(len(s) - 1):
        if s[i] != s[i + 1]:
            return False
    return True