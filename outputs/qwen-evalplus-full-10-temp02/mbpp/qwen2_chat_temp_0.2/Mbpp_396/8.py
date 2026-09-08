def check_char(s):
    # Check if the string starts and ends with the same character
    if s[0] == s[-1]:
        return "Valid"
    else:
        return "Invalid"