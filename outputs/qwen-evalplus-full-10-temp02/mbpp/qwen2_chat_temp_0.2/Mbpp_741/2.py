def all_Characters_Same(s):
    # Check if the string has only one character
    if len(s) <= 1:
        return True
    # Compare each character with the next one
    for i in range(len(s) - 1):
        if s[i] != s[i + 1]:
            return False
    return True